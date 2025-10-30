"""
Data validation rules engine for quality checks and constraints
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, date
import re
from abc import ABC, abstractmethod

import pandas as pd
import numpy as np


@dataclass
class ValidationResult:
    """Result of a validation check"""
    rule_name: str
    passed: bool
    error_message: Optional[str] = None
    error_count: int = 0
    total_count: int = 0
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_count == 0:
            return 100.0
        return ((self.total_count - self.error_count) / self.total_count) * 100


@dataclass
class DatasetValidationReport:
    """Complete validation report for a dataset"""
    dataset_name: str
    validation_timestamp: str
    total_rules: int
    passed_rules: int
    failed_rules: int
    
    validation_results: List[ValidationResult]
    
    overall_score: float
    severity_counts: Dict[str, int]
    
    @property
    def success_rate(self) -> float:
        """Overall success rate"""
        if self.total_rules == 0:
            return 100.0
        return (self.passed_rules / self.total_rules) * 100


class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(self, name: str, severity: str = "ERROR"):
        self.name = name
        self.severity = severity
    
    @abstractmethod
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        """Execute the validation rule"""
        pass


class NotNullRule(ValidationRule):
    """Validate that specified columns don't have null values"""
    
    def __init__(self, columns: List[str], severity: str = "ERROR"):
        super().__init__(f"not_null_{','.join(columns)}", severity)
        self.columns = columns
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        errors = 0
        total = len(data)
        error_messages = []
        
        for column in self.columns:
            if column not in data.columns:
                return ValidationResult(
                    rule_name=self.name,
                    passed=False,
                    error_message=f"Column '{column}' not found in dataset",
                    severity=self.severity
                )
            
            null_count = data[column].isnull().sum()
            if null_count > 0:
                errors += null_count
                error_messages.append(f"Column '{column}' has {null_count} null values")
        
        return ValidationResult(
            rule_name=self.name,
            passed=errors == 0,
            error_message="; ".join(error_messages) if error_messages else None,
            error_count=errors,
            total_count=total * len(self.columns),
            severity=self.severity
        )


class UniqueRule(ValidationRule):
    """Validate that specified columns have unique values"""
    
    def __init__(self, columns: List[str], severity: str = "ERROR"):
        super().__init__(f"unique_{','.join(columns)}", severity)
        self.columns = columns
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        error_messages = []
        total_errors = 0
        
        for column in self.columns:
            if column not in data.columns:
                return ValidationResult(
                    rule_name=self.name,
                    passed=False,
                    error_message=f"Column '{column}' not found in dataset",
                    severity=self.severity
                )
            
            total_count = len(data[column])
            unique_count = data[column].nunique()
            duplicate_count = total_count - unique_count
            
            if duplicate_count > 0:
                total_errors += duplicate_count
                error_messages.append(f"Column '{column}' has {duplicate_count} duplicate values")
        
        return ValidationResult(
            rule_name=self.name,
            passed=total_errors == 0,
            error_message="; ".join(error_messages) if error_messages else None,
            error_count=total_errors,
            total_count=len(data) * len(self.columns),
            severity=self.severity
        )


class RangeRule(ValidationRule):
    """Validate numeric values are within specified range"""
    
    def __init__(self, column: str, min_value: Optional[float] = None, 
                 max_value: Optional[float] = None, severity: str = "ERROR"):
        super().__init__(f"range_{column}_{min_value}_{max_value}", severity)
        self.column = column
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Column '{self.column}' not found in dataset",
                severity=self.severity
            )
        
        column_data = data[self.column].dropna()
        total_count = len(column_data)
        error_count = 0
        error_messages = []
        
        if self.min_value is not None:
            below_min = (column_data < self.min_value).sum()
            error_count += below_min
            if below_min > 0:
                error_messages.append(f"{below_min} values below minimum {self.min_value}")
        
        if self.max_value is not None:
            above_max = (column_data > self.max_value).sum()
            error_count += above_max
            if above_max > 0:
                error_messages.append(f"{above_max} values above maximum {self.max_value}")
        
        return ValidationResult(
            rule_name=self.name,
            passed=error_count == 0,
            error_message="; ".join(error_messages) if error_messages else None,
            error_count=error_count,
            total_count=total_count,
            severity=self.severity
        )


class PatternRule(ValidationRule):
    """Validate string values match a regex pattern"""
    
    def __init__(self, column: str, pattern: str, severity: str = "ERROR"):
        super().__init__(f"pattern_{column}", severity)
        self.column = column
        self.pattern = re.compile(pattern)
        self.pattern_string = pattern
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Column '{self.column}' not found in dataset",
                severity=self.severity
            )
        
        column_data = data[self.column].dropna().astype(str)
        total_count = len(column_data)
        
        # Check which values don't match the pattern
        matches = column_data.str.match(self.pattern)
        error_count = (~matches).sum()
        
        error_message = None
        if error_count > 0:
            error_message = f"{error_count} values don't match pattern '{self.pattern_string}'"
        
        return ValidationResult(
            rule_name=self.name,
            passed=error_count == 0,
            error_message=error_message,
            error_count=error_count,
            total_count=total_count,
            severity=self.severity
        )


class ValueSetRule(ValidationRule):
    """Validate that values are within a specified set"""
    
    def __init__(self, column: str, allowed_values: List[Any], severity: str = "ERROR"):
        super().__init__(f"value_set_{column}", severity)
        self.column = column
        self.allowed_values = set(allowed_values)
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Column '{self.column}' not found in dataset",
                severity=self.severity
            )
        
        column_data = data[self.column].dropna()
        total_count = len(column_data)
        
        # Find values not in allowed set
        invalid_values = column_data[~column_data.isin(self.allowed_values)]
        error_count = len(invalid_values)
        
        error_message = None
        if error_count > 0:
            unique_invalid = invalid_values.unique()[:5]  # Show first 5 invalid values
            error_message = f"{error_count} values not in allowed set. Examples: {list(unique_invalid)}"
        
        return ValidationResult(
            rule_name=self.name,
            passed=error_count == 0,
            error_message=error_message,
            error_count=error_count,
            total_count=total_count,
            severity=self.severity
        )


class DateRangeRule(ValidationRule):
    """Validate dates are within a specified range"""
    
    def __init__(self, column: str, min_date: Optional[Union[str, date]] = None, 
                 max_date: Optional[Union[str, date]] = None, severity: str = "ERROR"):
        super().__init__(f"date_range_{column}", severity)
        self.column = column
        
        # Convert string dates to datetime objects
        if isinstance(min_date, str):
            self.min_date = pd.to_datetime(min_date)
        else:
            self.min_date = min_date
            
        if isinstance(max_date, str):
            self.max_date = pd.to_datetime(max_date)
        else:
            self.max_date = max_date
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Column '{self.column}' not found in dataset",
                severity=self.severity
            )
        
        try:
            column_data = pd.to_datetime(data[self.column]).dropna()
        except:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Column '{self.column}' cannot be converted to datetime",
                severity=self.severity
            )
        
        total_count = len(column_data)
        error_count = 0
        error_messages = []
        
        if self.min_date is not None:
            before_min = (column_data < self.min_date).sum()
            error_count += before_min
            if before_min > 0:
                error_messages.append(f"{before_min} dates before {self.min_date}")
        
        if self.max_date is not None:
            after_max = (column_data > self.max_date).sum()
            error_count += after_max
            if after_max > 0:
                error_messages.append(f"{after_max} dates after {self.max_date}")
        
        return ValidationResult(
            rule_name=self.name,
            passed=error_count == 0,
            error_message="; ".join(error_messages) if error_messages else None,
            error_count=error_count,
            total_count=total_count,
            severity=self.severity
        )


class CustomRule(ValidationRule):
    """Custom validation rule with user-defined function"""
    
    def __init__(self, name: str, validation_func: Callable[[pd.DataFrame], ValidationResult], 
                 severity: str = "ERROR"):
        super().__init__(name, severity)
        self.validation_func = validation_func
    
    def validate(self, data: pd.DataFrame, **kwargs) -> ValidationResult:
        try:
            result = self.validation_func(data)
            result.severity = self.severity
            return result
        except Exception as e:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                error_message=f"Custom validation failed: {str(e)}",
                severity=self.severity
            )


class DataValidator:
    """Main data validation engine"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.logger = logging.getLogger(__name__)
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.rules.append(rule)
    
    def add_rules(self, rules: List[ValidationRule]):
        """Add multiple validation rules"""
        self.rules.extend(rules)
    
    def remove_rule(self, rule_name: str):
        """Remove a validation rule by name"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
    
    def clear_rules(self):
        """Clear all validation rules"""
        self.rules = []
    
    def validate_dataset(self, data: pd.DataFrame, dataset_name: str = "dataset") -> DatasetValidationReport:
        """Validate a dataset against all rules"""
        
        validation_results = []
        passed_count = 0
        failed_count = 0
        severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        
        for rule in self.rules:
            try:
                result = rule.validate(data)
                validation_results.append(result)
                
                if result.passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                severity_counts[result.severity] = severity_counts.get(result.severity, 0) + 1
                
            except Exception as e:
                self.logger.error(f"Error executing rule {rule.name}: {str(e)}")
                error_result = ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    error_message=f"Rule execution failed: {str(e)}",
                    severity="ERROR"
                )
                validation_results.append(error_result)
                failed_count += 1
                severity_counts["ERROR"] += 1
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(validation_results)
        
        return DatasetValidationReport(
            dataset_name=dataset_name,
            validation_timestamp=datetime.utcnow().isoformat(),
            total_rules=len(self.rules),
            passed_rules=passed_count,
            failed_rules=failed_count,
            validation_results=validation_results,
            overall_score=overall_score,
            severity_counts=severity_counts
        )
    
    def _calculate_overall_score(self, results: List[ValidationResult]) -> float:
        """Calculate weighted overall score"""
        if not results:
            return 100.0
        
        # Weight by severity
        weights = {"ERROR": 1.0, "WARNING": 0.5, "INFO": 0.1}
        
        total_weight = 0
        weighted_score = 0
        
        for result in results:
            weight = weights.get(result.severity, 1.0)
            total_weight += weight
            
            if result.passed:
                weighted_score += weight * 100
            else:
                # Partial credit based on success rate
                weighted_score += weight * result.success_rate
        
        return weighted_score / total_weight if total_weight > 0 else 100.0
    
    def load_rules_from_config(self, config: Dict[str, Any]):
        """Load validation rules from configuration"""
        self.clear_rules()
        
        for rule_config in config.get('rules', []):
            rule = self._create_rule_from_config(rule_config)
            if rule:
                self.add_rule(rule)
    
    def _create_rule_from_config(self, config: Dict[str, Any]) -> Optional[ValidationRule]:
        """Create a validation rule from configuration"""
        rule_type = config.get('type')
        severity = config.get('severity', 'ERROR')
        
        if rule_type == 'not_null':
            return NotNullRule(config['columns'], severity)
        
        elif rule_type == 'unique':
            return UniqueRule(config['columns'], severity)
        
        elif rule_type == 'range':
            return RangeRule(
                config['column'],
                config.get('min_value'),
                config.get('max_value'),
                severity
            )
        
        elif rule_type == 'pattern':
            return PatternRule(config['column'], config['pattern'], severity)
        
        elif rule_type == 'value_set':
            return ValueSetRule(config['column'], config['allowed_values'], severity)
        
        elif rule_type == 'date_range':
            return DateRangeRule(
                config['column'],
                config.get('min_date'),
                config.get('max_date'),
                severity
            )
        
        else:
            self.logger.warning(f"Unknown rule type: {rule_type}")
            return None
    
    def save_report_to_json(self, report: DatasetValidationReport, output_path: str):
        """Save validation report to JSON file"""
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
    
    def generate_html_report(self, report: DatasetValidationReport) -> str:
        """Generate HTML validation report"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Validation Report - {report.dataset_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; justify-content: space-between; margin: 20px 0; }}
                .metric {{ text-align: center; padding: 10px; background-color: #e7f3ff; border-radius: 5px; }}
                .rules {{ margin-top: 20px; }}
                .rule {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }}
                .rule.passed {{ border-left-color: #4CAF50; background-color: #f1f8e9; }}
                .rule.failed {{ border-left-color: #f44336; background-color: #ffebee; }}
                .rule.warning {{ border-left-color: #ff9800; background-color: #fff3e0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Data Validation Report</h1>
                <p><strong>Dataset:</strong> {report.dataset_name}</p>
                <p><strong>Validation Time:</strong> {report.validation_timestamp}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>{report.overall_score:.1f}%</h3>
                    <p>Overall Score</p>
                </div>
                <div class="metric">
                    <h3>{report.passed_rules}</h3>
                    <p>Passed Rules</p>
                </div>
                <div class="metric">
                    <h3>{report.failed_rules}</h3>
                    <p>Failed Rules</p>
                </div>
                <div class="metric">
                    <h3>{report.severity_counts.get('ERROR', 0)}</h3>
                    <p>Errors</p>
                </div>
            </div>
            
            <div class="rules">
                <h2>Validation Results</h2>
        """
        
        for result in report.validation_results:
            status_class = "passed" if result.passed else "failed"
            if result.severity == "WARNING":
                status_class = "warning"
            
            status_text = "✓ PASSED" if result.passed else "✗ FAILED"
            error_text = f"<br><em>{result.error_message}</em>" if result.error_message else ""
            success_rate_text = f" (Success Rate: {result.success_rate:.1f}%)" if result.total_count > 0 else ""
            
            html += f"""
                <div class="rule {status_class}">
                    <strong>{result.rule_name}</strong> - {status_text}{success_rate_text}
                    <span style="float: right; color: #666;">{result.severity}</span>
                    {error_text}
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html


# Example usage and configuration templates
def create_sample_validation_config() -> Dict[str, Any]:
    """Create a sample validation configuration"""
    return {
        "rules": [
            {
                "type": "not_null",
                "columns": ["id", "name", "email"],
                "severity": "ERROR"
            },
            {
                "type": "unique",
                "columns": ["id", "email"],
                "severity": "ERROR"
            },
            {
                "type": "range",
                "column": "age",
                "min_value": 0,
                "max_value": 120,
                "severity": "ERROR"
            },
            {
                "type": "pattern",
                "column": "email",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "severity": "ERROR"
            },
            {
                "type": "value_set",
                "column": "status",
                "allowed_values": ["active", "inactive", "pending"],
                "severity": "WARNING"
            },
            {
                "type": "date_range",
                "column": "created_at",
                "min_date": "2020-01-01",
                "max_date": "2025-12-31",
                "severity": "WARNING"
            }
        ]
    }


if __name__ == "__main__":
    # Example usage
    import pandas as pd
    import numpy as np
    
    # Create sample data
    data = {
        'id': [1, 2, 3, 4, 5, 2],  # Duplicate ID
        'name': ['Alice', 'Bob', 'Charlie', None, 'Eve', 'Frank'],  # Null name
        'email': ['alice@example.com', 'bob@invalid', 'charlie@example.com', 
                 'diana@example.com', 'eve@example.com', 'frank@example.com'],  # Invalid email
        'age': [25, 30, 150, 35, 28, 45],  # Out of range age
        'status': ['active', 'inactive', 'invalid_status', 'active', 'pending', 'active'],  # Invalid status
        'created_at': ['2023-01-01', '2023-02-01', '2030-01-01', '2023-04-01', '2023-05-01', '2023-06-01']  # Future date
    }
    
    df = pd.DataFrame(data)
    
    # Create validator and load rules
    validator = DataValidator()
    config = create_sample_validation_config()
    validator.load_rules_from_config(config)
    
    # Run validation
    report = validator.validate_dataset(df, "sample_dataset")
    
    # Print summary
    print(f"Validation Report for {report.dataset_name}")
    print(f"Overall Score: {report.overall_score:.1f}%")
    print(f"Rules: {report.passed_rules} passed, {report.failed_rules} failed")
    print()
    
    # Print individual results
    for result in report.validation_results:
        status = "✓" if result.passed else "✗"
        print(f"{status} {result.rule_name} ({result.severity})")
        if result.error_message:
            print(f"   {result.error_message}")
    
    # Save reports
    validator.save_report_to_json(report, "validation_report.json")
    
    html_report = validator.generate_html_report(report)
    with open("validation_report.html", "w") as f:
        f.write(html_report)
    
    print("\nReports saved to validation_report.json and validation_report.html")