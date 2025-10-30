"""
AI Data Analyst - Customer Feedback Collection System

Comprehensive feedback collection, analysis, and product improvement tracking
for MVP customers with automated insights and actionable recommendations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import json
import statistics
from collections import defaultdict, Counter
import re
from textblob import TextBlob
from google.cloud import firestore, storage, bigquery
from google.cloud.firestore_v1 import FieldFilter
import pandas as pd

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types of feedback that can be collected"""
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    USABILITY = "usability"
    PERFORMANCE = "performance"
    GENERAL = "general"
    SATISFACTION = "satisfaction"
    ONBOARDING = "onboarding"
    SUPPORT = "support"

class FeedbackChannel(Enum):
    """Channels through which feedback is collected"""
    IN_APP = "in_app"
    EMAIL = "email"
    SURVEY = "survey"
    INTERVIEW = "interview"
    SUPPORT_TICKET = "support_ticket"
    USER_TESTING = "user_testing"
    ANALYTICS = "analytics"

class FeedbackPriority(Enum):
    """Priority levels for feedback items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class FeedbackStatus(Enum):
    """Status of feedback processing"""
    NEW = "new"
    REVIEWED = "reviewed"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    COMPLETED = "completed"
    REJECTED = "rejected"

@dataclass
class FeedbackItem:
    """Individual feedback item"""
    id: str
    customer_id: str
    user_id: str
    feedback_type: FeedbackType
    channel: FeedbackChannel
    title: str
    description: str
    rating: Optional[int]  # 1-5 scale
    priority: FeedbackPriority
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    category: Optional[str]
    sentiment_score: Optional[float]  # -1 to 1
    metadata: Dict[str, Any]
    responses: List[Dict[str, Any]]

@dataclass
class FeedbackSummary:
    """Summary of feedback for a time period"""
    period_start: datetime
    period_end: datetime
    total_feedback: int
    avg_rating: float
    sentiment_distribution: Dict[str, int]
    top_categories: List[Tuple[str, int]]
    top_features_requested: List[Tuple[str, int]]
    critical_issues: List[str]
    satisfaction_score: float
    nps_score: Optional[float]

@dataclass
class ProductInsight:
    """Product insight derived from feedback analysis"""
    insight_id: str
    title: str
    description: str
    evidence: List[str]
    impact_score: float
    confidence_score: float
    recommended_action: str
    affected_customers: List[str]
    created_at: datetime
    category: str

class CustomerFeedbackCollector:
    """Main feedback collection and analysis system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize Google Cloud clients
        self.firestore_client = firestore.Client()
        self.storage_client = storage.Client()
        self.bigquery_client = bigquery.Client()
        
        # Collection references
        self.feedback_collection = self.firestore_client.collection('feedback')
        self.insights_collection = self.firestore_client.collection('product_insights')
        self.surveys_collection = self.firestore_client.collection('surveys')
        
        # Feedback processing
        self.feedback_processors = {
            FeedbackType.FEATURE_REQUEST: self._process_feature_request,
            FeedbackType.BUG_REPORT: self._process_bug_report,
            FeedbackType.USABILITY: self._process_usability_feedback,
            FeedbackType.PERFORMANCE: self._process_performance_feedback,
            FeedbackType.SATISFACTION: self._process_satisfaction_feedback
        }
        
        # Analytics and insights
        self.analytics_cache = {}
        self.insights_cache = {}
        
        logger.info("Customer Feedback Collection System initialized")
    
    async def collect_feedback(
        self, 
        customer_id: str, 
        user_id: str,
        feedback_type: FeedbackType,
        channel: FeedbackChannel,
        title: str,
        description: str,
        rating: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Collect new feedback from customer
        
        Args:
            customer_id: Customer identifier
            user_id: User who provided feedback
            feedback_type: Type of feedback
            channel: Channel through which feedback was received
            title: Feedback title/summary
            description: Detailed feedback description
            rating: Optional rating (1-5 scale)
            metadata: Additional metadata
            
        Returns:
            feedback_id: Unique identifier for the feedback
        """
        try:
            feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{customer_id}"
            
            # Analyze sentiment
            sentiment_score = self._analyze_sentiment(f"{title} {description}")
            
            # Extract categories and tags
            categories = self._extract_categories(description, feedback_type)
            tags = self._extract_tags(description)
            
            # Determine priority
            priority = self._determine_priority(feedback_type, sentiment_score, rating)
            
            # Create feedback item
            feedback_item = FeedbackItem(
                id=feedback_id,
                customer_id=customer_id,
                user_id=user_id,
                feedback_type=feedback_type,
                channel=channel,
                title=title,
                description=description,
                rating=rating,
                priority=priority,
                status=FeedbackStatus.NEW,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=tags,
                category=categories[0] if categories else None,
                sentiment_score=sentiment_score,
                metadata=metadata or {},
                responses=[]
            )
            
            # Save to Firestore
            await self._save_feedback_item(feedback_item)
            
            # Process feedback based on type
            if feedback_type in self.feedback_processors:
                await self.feedback_processors[feedback_type](feedback_item)
            
            # Trigger real-time analysis if high priority
            if priority in [FeedbackPriority.CRITICAL, FeedbackPriority.HIGH]:
                await self._trigger_immediate_analysis(feedback_item)
            
            # Update analytics
            await self._update_feedback_analytics(feedback_item)
            
            logger.info(f"Collected feedback {feedback_id} from customer {customer_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}")
            raise
    
    async def create_feedback_survey(
        self, 
        survey_name: str,
        questions: List[Dict[str, Any]],
        target_customers: List[str],
        survey_type: str = "satisfaction"
    ) -> str:
        """
        Create and distribute feedback survey
        
        Args:
            survey_name: Name of the survey
            questions: List of survey questions
            target_customers: Customer IDs to send survey to
            survey_type: Type of survey (satisfaction, feature, usability)
            
        Returns:
            survey_id: Unique identifier for the survey
        """
        try:
            survey_id = f"survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            survey_config = {
                'id': survey_id,
                'name': survey_name,
                'type': survey_type,
                'questions': questions,
                'target_customers': target_customers,
                'created_at': datetime.now(),
                'status': 'active',
                'responses': [],
                'completion_rate': 0.0,
                'avg_completion_time': 0.0
            }
            
            # Save survey configuration
            self.surveys_collection.document(survey_id).set(survey_config)
            
            # Send survey invitations
            for customer_id in target_customers:
                await self._send_survey_invitation(customer_id, survey_id, survey_config)
            
            logger.info(f"Created survey {survey_id} for {len(target_customers)} customers")
            return survey_id
            
        except Exception as e:
            logger.error(f"Failed to create survey: {e}")
            raise
    
    async def submit_survey_response(
        self, 
        survey_id: str, 
        customer_id: str, 
        user_id: str,
        responses: Dict[str, Any],
        completion_time_seconds: int
    ) -> bool:
        """
        Submit survey response
        
        Args:
            survey_id: Survey identifier
            customer_id: Customer who responded
            user_id: User who responded
            responses: Survey responses
            completion_time_seconds: Time taken to complete survey
            
        Returns:
            Success status
        """
        try:
            # Get survey configuration
            survey_doc = self.surveys_collection.document(survey_id).get()
            if not survey_doc.exists:
                raise ValueError(f"Survey {survey_id} not found")
            
            survey_data = survey_doc.to_dict()
            
            # Create response record
            response_record = {
                'customer_id': customer_id,
                'user_id': user_id,
                'responses': responses,
                'completion_time_seconds': completion_time_seconds,
                'submitted_at': datetime.now()
            }
            
            # Update survey with new response
            survey_data['responses'].append(response_record)
            
            # Update completion statistics
            total_responses = len(survey_data['responses'])
            survey_data['completion_rate'] = total_responses / len(survey_data['target_customers'])
            
            # Update average completion time
            completion_times = [r['completion_time_seconds'] for r in survey_data['responses']]
            survey_data['avg_completion_time'] = statistics.mean(completion_times)
            
            # Save updated survey
            self.surveys_collection.document(survey_id).set(survey_data)
            
            # Convert survey responses to feedback items
            await self._convert_survey_to_feedback(survey_id, response_record)
            
            logger.info(f"Survey response submitted for {survey_id} by customer {customer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit survey response: {e}")
            return False
    
    async def get_feedback_summary(
        self, 
        start_date: datetime, 
        end_date: datetime,
        customer_id: Optional[str] = None,
        feedback_type: Optional[FeedbackType] = None
    ) -> FeedbackSummary:
        """
        Get feedback summary for specified period and filters
        
        Args:
            start_date: Start date for summary
            end_date: End date for summary
            customer_id: Optional customer filter
            feedback_type: Optional feedback type filter
            
        Returns:
            Feedback summary with analytics
        """
        try:
            # Build query
            query = self.feedback_collection.where(
                filter=FieldFilter("created_at", ">=", start_date)
            ).where(
                filter=FieldFilter("created_at", "<=", end_date)
            )
            
            if customer_id:
                query = query.where(filter=FieldFilter("customer_id", "==", customer_id))
            
            if feedback_type:
                query = query.where(filter=FieldFilter("feedback_type", "==", feedback_type.value))
            
            # Execute query
            feedback_docs = query.stream()
            feedback_items = []
            
            for doc in feedback_docs:
                data = doc.to_dict()
                feedback_items.append(data)
            
            # Calculate summary statistics
            total_feedback = len(feedback_items)
            
            # Average rating
            ratings = [item['rating'] for item in feedback_items if item.get('rating')]
            avg_rating = statistics.mean(ratings) if ratings else 0.0
            
            # Sentiment distribution
            sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
            for item in feedback_items:
                score = item.get('sentiment_score', 0)
                if score > 0.1:
                    sentiment_distribution['positive'] += 1
                elif score < -0.1:
                    sentiment_distribution['negative'] += 1
                else:
                    sentiment_distribution['neutral'] += 1
            
            # Top categories
            categories = [item.get('category') for item in feedback_items if item.get('category')]
            category_counts = Counter(categories)
            top_categories = category_counts.most_common(5)
            
            # Top feature requests
            feature_requests = [
                item for item in feedback_items 
                if item.get('feedback_type') == FeedbackType.FEATURE_REQUEST.value
            ]
            feature_titles = [item['title'] for item in feature_requests]
            feature_counts = Counter(feature_titles)
            top_features_requested = feature_counts.most_common(5)
            
            # Critical issues
            critical_items = [
                item for item in feedback_items 
                if item.get('priority') == FeedbackPriority.CRITICAL.value
            ]
            critical_issues = [item['title'] for item in critical_items]
            
            # Satisfaction score (based on ratings and sentiment)
            satisfaction_components = []
            if ratings:
                rating_satisfaction = (statistics.mean(ratings) - 1) / 4  # Normalize to 0-1
                satisfaction_components.append(rating_satisfaction * 0.6)
            
            if feedback_items:
                sentiment_scores = [item.get('sentiment_score', 0) for item in feedback_items]
                sentiment_satisfaction = (statistics.mean(sentiment_scores) + 1) / 2  # Normalize to 0-1
                satisfaction_components.append(sentiment_satisfaction * 0.4)
            
            satisfaction_score = sum(satisfaction_components) if satisfaction_components else 0.5
            
            # NPS calculation (if we have sufficient rating data)
            nps_score = None
            if len(ratings) >= 10:
                promoters = len([r for r in ratings if r >= 4])
                detractors = len([r for r in ratings if r <= 2])
                nps_score = ((promoters - detractors) / len(ratings)) * 100
            
            summary = FeedbackSummary(
                period_start=start_date,
                period_end=end_date,
                total_feedback=total_feedback,
                avg_rating=round(avg_rating, 2),
                sentiment_distribution=sentiment_distribution,
                top_categories=top_categories,
                top_features_requested=top_features_requested,
                critical_issues=critical_issues,
                satisfaction_score=round(satisfaction_score, 3),
                nps_score=round(nps_score, 1) if nps_score else None
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            raise
    
    async def generate_product_insights(
        self, 
        lookback_days: int = 30,
        min_feedback_threshold: int = 5
    ) -> List[ProductInsight]:
        """
        Generate product insights from feedback analysis
        
        Args:
            lookback_days: Number of days to analyze
            min_feedback_threshold: Minimum feedback items needed for insight
            
        Returns:
            List of product insights with recommendations
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get feedback data
            feedback_summary = await self.get_feedback_summary(start_date, end_date)
            
            insights = []
            
            # Feature request analysis
            if len(feedback_summary.top_features_requested) > 0:
                for feature, count in feedback_summary.top_features_requested[:3]:
                    if count >= min_feedback_threshold:
                        insight = await self._generate_feature_insight(feature, count, start_date, end_date)
                        insights.append(insight)
            
            # Performance issue analysis
            performance_feedback = await self._get_performance_feedback(start_date, end_date)
            if len(performance_feedback) >= min_feedback_threshold:
                insight = await self._generate_performance_insight(performance_feedback)
                insights.append(insight)
            
            # Usability issue analysis
            usability_feedback = await self._get_usability_feedback(start_date, end_date)
            if len(usability_feedback) >= min_feedback_threshold:
                insight = await self._generate_usability_insight(usability_feedback)
                insights.append(insight)
            
            # Satisfaction trend analysis
            satisfaction_insight = await self._generate_satisfaction_insight(start_date, end_date)
            if satisfaction_insight:
                insights.append(satisfaction_insight)
            
            # Critical bug analysis
            critical_bugs = await self._get_critical_bugs(start_date, end_date)
            if critical_bugs:
                insight = await self._generate_critical_bug_insight(critical_bugs)
                insights.append(insight)
            
            # Save insights
            for insight in insights:
                await self._save_product_insight(insight)
            
            logger.info(f"Generated {len(insights)} product insights")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate product insights: {e}")
            raise
    
    async def get_customer_feedback_profile(self, customer_id: str) -> Dict[str, Any]:
        """
        Get comprehensive feedback profile for a customer
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Customer feedback profile with history and patterns
        """
        try:
            # Get all feedback from customer
            query = self.feedback_collection.where(
                filter=FieldFilter("customer_id", "==", customer_id)
            ).order_by("created_at", direction=firestore.Query.DESCENDING)
            
            feedback_docs = query.stream()
            feedback_items = [doc.to_dict() for doc in feedback_docs]
            
            if not feedback_items:
                return {
                    'customer_id': customer_id,
                    'total_feedback': 0,
                    'engagement_level': 'none'
                }
            
            # Calculate profile metrics
            total_feedback = len(feedback_items)
            avg_rating = statistics.mean([
                item['rating'] for item in feedback_items 
                if item.get('rating')
            ]) if any(item.get('rating') for item in feedback_items) else None
            
            # Feedback frequency
            first_feedback = min(item['created_at'] for item in feedback_items)
            days_active = (datetime.now() - first_feedback).days
            feedback_frequency = total_feedback / max(days_active, 1)
            
            # Engagement level
            if feedback_frequency > 0.5:
                engagement_level = 'high'
            elif feedback_frequency > 0.1:
                engagement_level = 'medium'
            else:
                engagement_level = 'low'
            
            # Feedback type distribution
            type_distribution = Counter([item['feedback_type'] for item in feedback_items])
            
            # Sentiment trend
            recent_items = feedback_items[:10]  # Last 10 feedback items
            recent_sentiment = statistics.mean([
                item.get('sentiment_score', 0) for item in recent_items
            ]) if recent_items else 0
            
            # Top categories
            categories = [item.get('category') for item in feedback_items if item.get('category')]
            top_categories = Counter(categories).most_common(3)
            
            profile = {
                'customer_id': customer_id,
                'total_feedback': total_feedback,
                'avg_rating': round(avg_rating, 2) if avg_rating else None,
                'feedback_frequency': round(feedback_frequency, 3),
                'engagement_level': engagement_level,
                'days_active': days_active,
                'first_feedback_date': first_feedback.isoformat(),
                'last_feedback_date': feedback_items[0]['created_at'].isoformat(),
                'feedback_type_distribution': dict(type_distribution),
                'recent_sentiment_trend': round(recent_sentiment, 3),
                'top_categories': top_categories,
                'satisfaction_trend': await self._calculate_satisfaction_trend(customer_id),
                'most_recent_feedback': feedback_items[:5]  # Last 5 feedback items
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get customer feedback profile for {customer_id}: {e}")
            raise
    
    async def export_feedback_data(
        self, 
        start_date: datetime, 
        end_date: datetime,
        format: str = "csv"
    ) -> str:
        """
        Export feedback data for analysis
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            format: Export format (csv, json, excel)
            
        Returns:
            File path or download URL
        """
        try:
            # Get feedback data
            query = self.feedback_collection.where(
                filter=FieldFilter("created_at", ">=", start_date)
            ).where(
                filter=FieldFilter("created_at", "<=", end_date)
            )
            
            feedback_docs = query.stream()
            feedback_data = []
            
            for doc in feedback_docs:
                data = doc.to_dict()
                # Flatten the data for export
                export_item = {
                    'id': data.get('id'),
                    'customer_id': data.get('customer_id'),
                    'user_id': data.get('user_id'),
                    'feedback_type': data.get('feedback_type'),
                    'channel': data.get('channel'),
                    'title': data.get('title'),
                    'description': data.get('description'),
                    'rating': data.get('rating'),
                    'priority': data.get('priority'),
                    'status': data.get('status'),
                    'created_at': data.get('created_at').isoformat() if data.get('created_at') else None,
                    'category': data.get('category'),
                    'sentiment_score': data.get('sentiment_score'),
                    'tags': ','.join(data.get('tags', [])),
                }
                feedback_data.append(export_item)
            
            # Create DataFrame
            df = pd.DataFrame(feedback_data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"feedback_export_{timestamp}.{format}"
            
            # Export based on format
            if format == "csv":
                file_path = f"/tmp/{filename}"
                df.to_csv(file_path, index=False)
            elif format == "json":
                file_path = f"/tmp/{filename}"
                df.to_json(file_path, orient='records', indent=2)
            elif format == "excel":
                file_path = f"/tmp/{filename}"
                df.to_excel(file_path, index=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Upload to Cloud Storage
            bucket_name = f"{self.config['project_id']}-feedback-exports"
            blob_name = f"exports/{filename}"
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            
            # Generate signed URL for download
            download_url = blob.generate_signed_url(
                expiration=timedelta(hours=24),
                method='GET'
            )
            
            logger.info(f"Exported {len(feedback_data)} feedback items to {filename}")
            return download_url
            
        except Exception as e:
            logger.error(f"Failed to export feedback data: {e}")
            raise
    
    # Helper methods
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of feedback text"""
        try:
            # Use TextBlob for basic sentiment analysis
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except:
            return 0.0
    
    def _extract_categories(self, text: str, feedback_type: FeedbackType) -> List[str]:
        """Extract categories from feedback text"""
        categories = []
        
        # Define category keywords
        category_keywords = {
            'data_connection': ['connect', 'database', 'sql', 'integration', 'import', 'export'],
            'visualization': ['chart', 'graph', 'dashboard', 'visualization', 'plot'],
            'performance': ['slow', 'fast', 'speed', 'performance', 'timeout', 'loading'],
            'ui_ux': ['interface', 'design', 'layout', 'navigation', 'user experience'],
            'analytics': ['analysis', 'analytics', 'insights', 'statistics', 'metrics'],
            'reporting': ['report', 'export', 'sharing', 'collaboration'],
            'security': ['security', 'privacy', 'permissions', 'access', 'authentication']
        }
        
        text_lower = text.lower()
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from feedback text"""
        tags = []
        
        # Simple keyword extraction
        keywords = ['urgent', 'important', 'suggestion', 'request', 'issue', 'problem', 'feature']
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword in text_lower:
                tags.append(keyword)
        
        return tags
    
    def _determine_priority(
        self, 
        feedback_type: FeedbackType, 
        sentiment_score: float, 
        rating: Optional[int]
    ) -> FeedbackPriority:
        """Determine priority based on feedback characteristics"""
        
        # Critical conditions
        if feedback_type == FeedbackType.BUG_REPORT and sentiment_score < -0.5:
            return FeedbackPriority.CRITICAL
        
        if rating and rating <= 2:
            return FeedbackPriority.HIGH
        
        # High priority conditions
        if feedback_type in [FeedbackType.BUG_REPORT, FeedbackType.PERFORMANCE]:
            return FeedbackPriority.HIGH
        
        if sentiment_score < -0.3:
            return FeedbackPriority.HIGH
        
        # Medium priority conditions
        if feedback_type == FeedbackType.FEATURE_REQUEST:
            return FeedbackPriority.MEDIUM
        
        if rating and rating == 3:
            return FeedbackPriority.MEDIUM
        
        # Default to low priority
        return FeedbackPriority.LOW
    
    async def _save_feedback_item(self, feedback_item: FeedbackItem):
        """Save feedback item to Firestore"""
        doc_data = asdict(feedback_item)
        # Convert datetime objects to timestamps
        doc_data['created_at'] = feedback_item.created_at
        doc_data['updated_at'] = feedback_item.updated_at
        
        self.feedback_collection.document(feedback_item.id).set(doc_data)
    
    async def _process_feature_request(self, feedback_item: FeedbackItem):
        """Process feature request feedback"""
        # Add to product backlog tracking
        logger.info(f"Processing feature request: {feedback_item.title}")
    
    async def _process_bug_report(self, feedback_item: FeedbackItem):
        """Process bug report feedback"""
        # Create issue in bug tracking system
        logger.info(f"Processing bug report: {feedback_item.title}")
    
    async def _process_usability_feedback(self, feedback_item: FeedbackItem):
        """Process usability feedback"""
        # Forward to UX team
        logger.info(f"Processing usability feedback: {feedback_item.title}")
    
    async def _process_performance_feedback(self, feedback_item: FeedbackItem):
        """Process performance feedback"""
        # Alert performance monitoring team
        logger.info(f"Processing performance feedback: {feedback_item.title}")
    
    async def _process_satisfaction_feedback(self, feedback_item: FeedbackItem):
        """Process satisfaction feedback"""
        # Update customer satisfaction metrics
        logger.info(f"Processing satisfaction feedback: {feedback_item.title}")
    
    async def _trigger_immediate_analysis(self, feedback_item: FeedbackItem):
        """Trigger immediate analysis for high-priority feedback"""
        logger.info(f"Triggering immediate analysis for {feedback_item.id}")
    
    async def _update_feedback_analytics(self, feedback_item: FeedbackItem):
        """Update real-time feedback analytics"""
        # Update analytics in BigQuery or other analytics store
        pass
    
    async def _send_survey_invitation(self, customer_id: str, survey_id: str, survey_config: Dict[str, Any]):
        """Send survey invitation to customer"""
        logger.info(f"Sending survey invitation {survey_id} to customer {customer_id}")
    
    async def _convert_survey_to_feedback(self, survey_id: str, response_record: Dict[str, Any]):
        """Convert survey responses to feedback items"""
        # Convert structured survey responses to feedback items
        pass
    
    async def _generate_feature_insight(self, feature: str, count: int, start_date: datetime, end_date: datetime) -> ProductInsight:
        """Generate insight for feature requests"""
        insight_id = f"insight_feature_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ProductInsight(
            insight_id=insight_id,
            title=f"High Demand Feature: {feature}",
            description=f"Feature '{feature}' has been requested {count} times in the last 30 days",
            evidence=[f"{count} customer requests", "High sentiment scores"],
            impact_score=min(count / 10.0, 1.0),
            confidence_score=0.8,
            recommended_action=f"Consider prioritizing '{feature}' for next release",
            affected_customers=[],  # Would be populated with actual customer IDs
            created_at=datetime.now(),
            category="feature_request"
        )
    
    async def _generate_performance_insight(self, performance_feedback: List[Dict[str, Any]]) -> ProductInsight:
        """Generate insight for performance issues"""
        insight_id = f"insight_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ProductInsight(
            insight_id=insight_id,
            title="Performance Issues Detected",
            description=f"Multiple performance complaints received ({len(performance_feedback)} reports)",
            evidence=[f"{len(performance_feedback)} performance reports", "Negative sentiment trend"],
            impact_score=0.8,
            confidence_score=0.9,
            recommended_action="Investigate and optimize performance bottlenecks",
            affected_customers=[fb['customer_id'] for fb in performance_feedback],
            created_at=datetime.now(),
            category="performance"
        )
    
    async def _generate_usability_insight(self, usability_feedback: List[Dict[str, Any]]) -> ProductInsight:
        """Generate insight for usability issues"""
        insight_id = f"insight_usability_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ProductInsight(
            insight_id=insight_id,
            title="Usability Concerns Identified",
            description=f"Users reporting usability issues ({len(usability_feedback)} reports)",
            evidence=[f"{len(usability_feedback)} usability reports", "Common UI/UX complaints"],
            impact_score=0.6,
            confidence_score=0.7,
            recommended_action="Conduct UX review and implement improvements",
            affected_customers=[fb['customer_id'] for fb in usability_feedback],
            created_at=datetime.now(),
            category="usability"
        )
    
    async def _generate_satisfaction_insight(self, start_date: datetime, end_date: datetime) -> Optional[ProductInsight]:
        """Generate insight for satisfaction trends"""
        # Get satisfaction data
        summary = await self.get_feedback_summary(start_date, end_date)
        
        if summary.satisfaction_score < 0.6:
            insight_id = f"insight_satisfaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return ProductInsight(
                insight_id=insight_id,
                title="Customer Satisfaction Declining",
                description=f"Overall satisfaction score is {summary.satisfaction_score:.2f}",
                evidence=[f"Satisfaction score: {summary.satisfaction_score:.2f}", "Negative sentiment trend"],
                impact_score=0.9,
                confidence_score=0.8,
                recommended_action="Investigate root causes and implement satisfaction improvement plan",
                affected_customers=[],
                created_at=datetime.now(),
                category="satisfaction"
            )
        
        return None
    
    async def _generate_critical_bug_insight(self, critical_bugs: List[Dict[str, Any]]) -> ProductInsight:
        """Generate insight for critical bugs"""
        insight_id = f"insight_bugs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ProductInsight(
            insight_id=insight_id,
            title="Critical Bugs Reported",
            description=f"Multiple critical bugs reported ({len(critical_bugs)} reports)",
            evidence=[f"{len(critical_bugs)} critical bug reports", "High priority issues"],
            impact_score=1.0,
            confidence_score=0.95,
            recommended_action="Immediately address critical bugs before next release",
            affected_customers=[bug['customer_id'] for bug in critical_bugs],
            created_at=datetime.now(),
            category="bugs"
        )
    
    async def _save_product_insight(self, insight: ProductInsight):
        """Save product insight to Firestore"""
        doc_data = asdict(insight)
        doc_data['created_at'] = insight.created_at
        
        self.insights_collection.document(insight.insight_id).set(doc_data)
    
    async def _get_performance_feedback(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get performance-related feedback"""
        query = self.feedback_collection.where(
            filter=FieldFilter("feedback_type", "==", FeedbackType.PERFORMANCE.value)
        ).where(
            filter=FieldFilter("created_at", ">=", start_date)
        ).where(
            filter=FieldFilter("created_at", "<=", end_date)
        )
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    async def _get_usability_feedback(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get usability-related feedback"""
        query = self.feedback_collection.where(
            filter=FieldFilter("feedback_type", "==", FeedbackType.USABILITY.value)
        ).where(
            filter=FieldFilter("created_at", ">=", start_date)
        ).where(
            filter=FieldFilter("created_at", "<=", end_date)
        )
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    async def _get_critical_bugs(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get critical bug reports"""
        query = self.feedback_collection.where(
            filter=FieldFilter("feedback_type", "==", FeedbackType.BUG_REPORT.value)
        ).where(
            filter=FieldFilter("priority", "==", FeedbackPriority.CRITICAL.value)
        ).where(
            filter=FieldFilter("created_at", ">=", start_date)
        ).where(
            filter=FieldFilter("created_at", "<=", end_date)
        )
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    async def _calculate_satisfaction_trend(self, customer_id: str) -> Dict[str, Any]:
        """Calculate satisfaction trend for customer"""
        # Get last 90 days of feedback
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        query = self.feedback_collection.where(
            filter=FieldFilter("customer_id", "==", customer_id)
        ).where(
            filter=FieldFilter("created_at", ">=", start_date)
        ).order_by("created_at")
        
        docs = query.stream()
        feedback_items = [doc.to_dict() for doc in docs]
        
        if len(feedback_items) < 2:
            return {'trend': 'insufficient_data', 'change': 0.0}
        
        # Calculate trend over time
        ratings = [item['rating'] for item in feedback_items if item.get('rating')]
        sentiments = [item.get('sentiment_score', 0) for item in feedback_items]
        
        if ratings:
            first_half_rating = statistics.mean(ratings[:len(ratings)//2]) if len(ratings) >= 4 else ratings[0]
            second_half_rating = statistics.mean(ratings[len(ratings)//2:]) if len(ratings) >= 4 else ratings[-1]
            rating_trend = second_half_rating - first_half_rating
        else:
            rating_trend = 0
        
        if sentiments:
            first_half_sentiment = statistics.mean(sentiments[:len(sentiments)//2]) if len(sentiments) >= 4 else sentiments[0]
            second_half_sentiment = statistics.mean(sentiments[len(sentiments)//2:]) if len(sentiments) >= 4 else sentiments[-1]
            sentiment_trend = second_half_sentiment - first_half_sentiment
        else:
            sentiment_trend = 0
        
        # Combine trends
        overall_trend = (rating_trend * 0.6 + sentiment_trend * 0.4) if ratings else sentiment_trend
        
        if abs(overall_trend) < 0.1:
            trend_direction = 'stable'
        elif overall_trend > 0:
            trend_direction = 'improving'
        else:
            trend_direction = 'declining'
        
        return {
            'trend': trend_direction,
            'change': round(overall_trend, 3),
            'data_points': len(feedback_items)
        }


# Usage example
async def main():
    """Example usage of Customer Feedback Collection System"""
    
    config = {
        'project_id': 'ai-data-analyst-prod'
    }
    
    feedback_system = CustomerFeedbackCollector(config)
    
    # Collect feedback
    feedback_id = await feedback_system.collect_feedback(
        customer_id='customer_001',
        user_id='user_123',
        feedback_type=FeedbackType.FEATURE_REQUEST,
        channel=FeedbackChannel.IN_APP,
        title='Need better data visualization options',
        description='Would love to see more chart types, especially heatmaps and treemaps for our analytics dashboard.',
        rating=4,
        metadata={'feature_area': 'visualization', 'urgency': 'medium'}
    )
    
    print(f"Collected feedback: {feedback_id}")
    
    # Get feedback summary
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    summary = await feedback_system.get_feedback_summary(start_date, end_date)
    print(f"Total feedback in last 30 days: {summary.total_feedback}")
    print(f"Average rating: {summary.avg_rating}")
    print(f"Satisfaction score: {summary.satisfaction_score}")
    
    # Generate insights
    insights = await feedback_system.generate_product_insights(lookback_days=30)
    print(f"Generated {len(insights)} product insights")
    
    for insight in insights[:3]:  # Show first 3 insights
        print(f"- {insight.title}: {insight.description}")

if __name__ == "__main__":
    asyncio.run(main())