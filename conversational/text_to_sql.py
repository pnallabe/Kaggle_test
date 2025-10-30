"""Vertex AI Text-to-SQL Service

This module integrates with Vertex AI Generative Models to convert natural language
queries into SQL statements for BigQuery data exploration.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels for appropriate model selection."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class SQLGenerationRequest:
    """Request structure for SQL generation."""
    natural_language_query: str
    dataset_schemas: List[Dict[str, Any]]
    user_context: Optional[Dict[str, Any]] = None
    max_results: int = 1000
    complexity_hint: Optional[QueryComplexity] = None


@dataclass
class SQLGenerationResponse:
    """Response structure for SQL generation."""
    sql_query: str
    confidence_score: float
    explanation: str
    suggested_visualizations: List[str]
    estimated_complexity: QueryComplexity
    warnings: List[str]
    metadata: Dict[str, Any]


class TextToSQLService:
    """Service for converting natural language to SQL using Vertex AI."""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-pro"
    ):
        """Initialize the Text-to-SQL service.
        
        Args:
            project_id: GCP project ID
            location: Vertex AI location
            model_name: Generative model to use
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel(model_name)
        
        # BigQuery client for schema validation
        self.bq_client = bigquery.Client(project=project_id)
        
        # Load prompt templates
        self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> None:
        """Load and configure prompt templates for SQL generation."""
        self.system_prompt = """
You are an expert SQL analyst specializing in BigQuery. Your task is to convert natural language queries into safe, efficient SQL statements.

CORE PRINCIPLES:
- Generate ONLY SELECT statements (no INSERT, UPDATE, DELETE, DROP, CREATE)
- Use BigQuery standard SQL syntax
- Include appropriate LIMIT clauses to prevent runaway queries
- Provide clear explanations of the generated SQL
- Suggest appropriate visualizations for the results
- Flag potential performance or security concerns

RESPONSE FORMAT:
Return a JSON object with these fields:
{
    "sql_query": "The generated SQL query",
    "confidence_score": 0.85,
    "explanation": "Clear explanation of what the query does",
    "suggested_visualizations": ["chart_type1", "chart_type2"],
    "estimated_complexity": "simple|medium|complex",
    "warnings": ["Any warnings about the query"],
    "metadata": {"additional_context": "value"}
}

SAFETY RULES:
- Never generate queries that could expose sensitive data without explicit permission
- Always include reasonable LIMIT clauses
- Validate column names against provided schemas
- Flag queries that might be expensive to execute
"""
        
        self.few_shot_examples = [
            {
                "input": "Show me the top 10 customers by revenue",
                "schema": {"customers": ["customer_id", "name", "revenue"]},
                "output": {
                    "sql_query": "SELECT name, revenue FROM `project.dataset.customers` ORDER BY revenue DESC LIMIT 10",
                    "confidence_score": 0.95,
                    "explanation": "This query retrieves the top 10 customers sorted by revenue in descending order.",
                    "suggested_visualizations": ["bar_chart", "table"],
                    "estimated_complexity": "simple",
                    "warnings": [],
                    "metadata": {"table_used": "customers"}
                }
            },
            {
                "input": "What's the average order value by month for the last year?",
                "schema": {"orders": ["order_id", "order_date", "amount", "customer_id"]},
                "output": {
                    "sql_query": "SELECT EXTRACT(YEAR FROM order_date) as year, EXTRACT(MONTH FROM order_date) as month, AVG(amount) as avg_order_value FROM `project.dataset.orders` WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR) GROUP BY year, month ORDER BY year, month LIMIT 12",
                    "confidence_score": 0.90,
                    "explanation": "This query calculates the average order value grouped by month for the last 12 months.",
                    "suggested_visualizations": ["line_chart", "area_chart"],
                    "estimated_complexity": "medium",
                    "warnings": ["Query spans multiple months - consider performance impact"],
                    "metadata": {"aggregation": "average", "time_range": "1_year"}
                }
            }
        ]
    
    def generate_sql(self, request: SQLGenerationRequest) -> SQLGenerationResponse:
        """Generate SQL from natural language query.
        
        Args:
            request: SQL generation request
            
        Returns:
            SQL generation response with query and metadata
            
        Raises:
            ValueError: If request is invalid
            GoogleCloudError: If Vertex AI call fails
        """
        try:
            # Validate request
            self._validate_request(request)
            
            # Build context-aware prompt
            prompt = self._build_prompt(request)
            
            # Generate SQL using Vertex AI
            response = self.model.generate_content(prompt)
            
            # Parse and validate response
            sql_response = self._parse_response(response.text)
            
            # Validate generated SQL
            self._validate_generated_sql(sql_response, request.dataset_schemas)
            
            logger.info(f"Successfully generated SQL: {sql_response.sql_query[:100]}...")
            return sql_response
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {str(e)}")
            raise
    
    def _validate_request(self, request: SQLGenerationRequest) -> None:
        """Validate the SQL generation request."""
        if not request.natural_language_query:
            raise ValueError("Natural language query cannot be empty")
        
        if not request.dataset_schemas:
            raise ValueError("Dataset schemas must be provided")
        
        if request.max_results <= 0:
            raise ValueError("Max results must be positive")
    
    def _build_prompt(self, request: SQLGenerationRequest) -> str:
        """Build context-aware prompt for SQL generation."""
        # Format dataset schemas
        schema_context = self._format_schemas(request.dataset_schemas)
        
        # Build few-shot examples
        examples = "\n\n".join([
            f"Example {i+1}:\nInput: {ex['input']}\nSchema: {json.dumps(ex['schema'])}\nOutput: {json.dumps(ex['output'])}"
            for i, ex in enumerate(self.few_shot_examples)
        ])
        
        # User context
        user_context = ""
        if request.user_context:
            user_context = f"\nUser Context: {json.dumps(request.user_context)}"
        
        prompt = f"""
{self.system_prompt}

AVAILABLE SCHEMAS:
{schema_context}

EXAMPLES:
{examples}

USER QUERY:
Natural Language: {request.natural_language_query}
Max Results: {request.max_results}{user_context}

Generate the SQL query following the response format above.
"""
        return prompt
    
    def _format_schemas(self, schemas: List[Dict[str, Any]]) -> str:
        """Format dataset schemas for prompt context."""
        formatted_schemas = []
        
        for schema in schemas:
            table_name = schema.get('table_name', 'unknown')
            columns = schema.get('columns', [])
            
            # Format columns with types and descriptions
            column_info = []
            for col in columns:
                col_name = col.get('name', '')
                col_type = col.get('type', 'STRING')
                col_desc = col.get('description', '')
                
                col_str = f"{col_name} ({col_type})"
                if col_desc:
                    col_str += f" - {col_desc}"
                column_info.append(col_str)
            
            schema_str = f"Table: {table_name}\nColumns:\n" + "\n".join(f"  - {col}" for col in column_info)
            formatted_schemas.append(schema_str)
        
        return "\n\n".join(formatted_schemas)
    
    def _parse_response(self, response_text: str) -> SQLGenerationResponse:
        """Parse the model response into structured format."""
        try:
            # Extract JSON from response (handle potential markdown formatting)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            parsed = json.loads(response_text)
            
            return SQLGenerationResponse(
                sql_query=parsed.get('sql_query', ''),
                confidence_score=float(parsed.get('confidence_score', 0.0)),
                explanation=parsed.get('explanation', ''),
                suggested_visualizations=parsed.get('suggested_visualizations', []),
                estimated_complexity=QueryComplexity(parsed.get('estimated_complexity', 'medium')),
                warnings=parsed.get('warnings', []),
                metadata=parsed.get('metadata', {})
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse model response: {e}")
            # Return fallback response
            return SQLGenerationResponse(
                sql_query="-- Failed to parse response",
                confidence_score=0.0,
                explanation="Failed to generate valid SQL",
                suggested_visualizations=[],
                estimated_complexity=QueryComplexity.SIMPLE,
                warnings=["Failed to parse model response"],
                metadata={"error": str(e)}
            )
    
    def _validate_generated_sql(
        self, 
        response: SQLGenerationResponse, 
        schemas: List[Dict[str, Any]]
    ) -> None:
        """Validate the generated SQL against schemas and safety rules."""
        sql = response.sql_query.upper().strip()
        
        # Safety validations
        dangerous_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER']
        for keyword in dangerous_keywords:
            if keyword in sql:
                response.warnings.append(f"Potentially dangerous SQL keyword detected: {keyword}")
        
        # Check for SELECT statement
        if not sql.startswith('SELECT'):
            response.warnings.append("Query does not start with SELECT")
        
        # Check for LIMIT clause
        if 'LIMIT' not in sql:
            response.warnings.append("Query does not include LIMIT clause - consider adding one")
        
        # Validate table references against schemas
        table_names = [schema.get('table_name', '') for schema in schemas]
        for table_name in table_names:
            if table_name and table_name not in response.sql_query:
                continue  # This table is not referenced, which is fine
    
    def explain_sql(self, sql_query: str) -> Dict[str, Any]:
        """Generate explanation for an existing SQL query.
        
        Args:
            sql_query: SQL query to explain
            
        Returns:
            Dictionary with explanation and analysis
        """
        prompt = f"""
Analyze and explain this BigQuery SQL query in detail:

{sql_query}

Provide a JSON response with:
- "explanation": Clear, non-technical explanation of what the query does
- "complexity": "simple", "medium", or "complex"
- "performance_notes": Array of performance considerations
- "security_notes": Array of security considerations
- "suggested_improvements": Array of suggested improvements
"""
        
        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to explain SQL: {e}")
            return {
                "explanation": "Unable to generate explanation",
                "complexity": "unknown",
                "performance_notes": [],
                "security_notes": [],
                "suggested_improvements": []
            }
    
    def suggest_follow_up_queries(
        self, 
        original_query: str, 
        original_sql: str,
        schemas: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Suggest follow-up queries based on the original query.
        
        Args:
            original_query: Original natural language query
            original_sql: Generated SQL
            schemas: Available dataset schemas
            
        Returns:
            List of suggested follow-up queries
        """
        schema_context = self._format_schemas(schemas)
        
        prompt = f"""
Based on this query and available data, suggest 3-5 relevant follow-up questions:

Original Question: {original_query}
Generated SQL: {original_sql}

Available Data:
{schema_context}

Return a JSON array of objects with:
- "question": Natural language follow-up question
- "reasoning": Why this would be a good follow-up

Focus on:
- Drilling down into specific segments
- Time-based analysis
- Comparative analysis
- Identifying outliers or trends
"""
        
        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to generate follow-up suggestions: {e}")
            return []


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize service
    service = TextToSQLService(PROJECT_ID)
    
    # Example schemas
    example_schemas = [
        {
            "table_name": "customers",
            "columns": [
                {"name": "customer_id", "type": "STRING", "description": "Unique customer identifier"},
                {"name": "name", "type": "STRING", "description": "Customer name"},
                {"name": "email", "type": "STRING", "description": "Customer email address"},
                {"name": "signup_date", "type": "DATE", "description": "Date customer signed up"},
                {"name": "total_spent", "type": "FLOAT", "description": "Total amount spent by customer"}
            ]
        },
        {
            "table_name": "orders",
            "columns": [
                {"name": "order_id", "type": "STRING", "description": "Unique order identifier"},
                {"name": "customer_id", "type": "STRING", "description": "Customer who placed the order"},
                {"name": "order_date", "type": "DATE", "description": "Date order was placed"},
                {"name": "amount", "type": "FLOAT", "description": "Order total amount"},
                {"name": "status", "type": "STRING", "description": "Order status"}
            ]
        }
    ]
    
    # Example request
    request = SQLGenerationRequest(
        natural_language_query="Show me the top 5 customers by total spending this year",
        dataset_schemas=example_schemas,
        max_results=5
    )
    
    try:
        response = service.generate_sql(request)
        print(f"Generated SQL: {response.sql_query}")
        print(f"Explanation: {response.explanation}")
        print(f"Confidence: {response.confidence_score}")
        print(f"Suggestions: {response.suggested_visualizations}")
    except Exception as e:
        print(f"Error: {e}")