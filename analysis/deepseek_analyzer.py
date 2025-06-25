"""
Social Media Surveillance System - DeepSeek AI Analysis Engine
Comprehensive AI-powered content analysis using DeepSeek API for sentiment analysis,
topic extraction, behavioral pattern detection, and intelligent insights.
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re
import hashlib
import statistics
from collections import defaultdict, Counter

import requests
import numpy as np
from sqlalchemy.orm import Session

from core.config import config
from core.database import db_manager
from core.credentials_manager import get_credentials_manager
from models.instagram_models import SurveillanceTarget, Post, Follower, Story, ChangeLog

# Configure logging
logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of analysis that can be performed"""
    SENTIMENT = "sentiment"
    TOPICS = "topics"
    ENGAGEMENT_PREDICTION = "engagement_prediction"
    BOT_DETECTION = "bot_detection"
    INFLUENCE_SCORING = "influence_scoring"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    CONTENT_CATEGORIZATION = "content_categorization"
    TREND_DETECTION = "trend_detection"
    ANOMALY_DETECTION = "anomaly_detection"

class ModelType(Enum):
    """DeepSeek model types"""
    CHAT = "chat"
    CODER = "coder"

@dataclass
class AnalysisResult:
    """Container for analysis results"""
    analysis_type: AnalysisType
    confidence: float
    result: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'analysis_type': self.analysis_type.value,
            'confidence': self.confidence,
            'result': self.result,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'processing_time': self.processing_time
        }

@dataclass
class APIUsageStats:
    """Track API usage statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    rate_limit_hits: int = 0

class DeepSeekAPIClient:
    """
    Core DeepSeek API client with comprehensive error handling,
    rate limiting, and request management
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Try to get API key from multiple sources
        if api_key:
            self.api_key = api_key
        else:
            # Try credentials manager first, then config
            credentials_manager = get_credentials_manager()
            self.api_key = credentials_manager.get_deepseek_api_key() or config.deepseek.api_key

        self.base_url = config.deepseek.base_url
        self.timeout = config.deepseek.timeout

        if not self.api_key:
            logger.warning("DeepSeek API key not found. Analysis functions will return mock results.")
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'SocialMediaSurveillance/1.0'
        })
        
        # Rate limiting
        self.requests_per_minute = 20  # Reduced to be more conservative
        self.request_times = []
        self.max_retries = 3  # Maximum number of retries for rate limiting

        # Usage statistics
        self.usage_stats = APIUsageStats()
        
        logger.info("DeepSeek API client initialized")
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.usage_stats.rate_limit_hits += 1
        
        self.request_times.append(now)
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with error handling and retries"""
        self._check_rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()
        
        try:
            self.usage_stats.total_requests += 1
            
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            self.usage_stats.last_request_time = datetime.now(timezone.utc)
            
            # Update average response time
            if self.usage_stats.average_response_time == 0:
                self.usage_stats.average_response_time = processing_time
            else:
                self.usage_stats.average_response_time = (
                    self.usage_stats.average_response_time * 0.9 + processing_time * 0.1
                )
            
            if response.status_code == 200:
                self.usage_stats.successful_requests += 1
                result = response.json()
                
                # Track token usage if available
                if 'usage' in result:
                    self.usage_stats.total_tokens_used += result['usage'].get('total_tokens', 0)
                
                return result
            
            elif response.status_code == 429:
                # Rate limit exceeded
                self.usage_stats.rate_limit_hits += 1
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(endpoint, payload)  # Retry once
            
            else:
                self.usage_stats.failed_requests += 1
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            self.usage_stats.failed_requests += 1
            logger.error("API request timed out")
            raise Exception("API request timed out")
            
        except requests.exceptions.RequestException as e:
            self.usage_stats.failed_requests += 1
            logger.error(f"API request failed: {e}")
            raise Exception(f"API request failed: {e}")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """Make chat completion request"""
        payload = {
            'model': model or config.deepseek.model_chat,
            'messages': messages,
            'temperature': temperature or config.deepseek.temperature,
            'max_tokens': max_tokens or config.deepseek.max_tokens
        }
        
        return self._make_request('chat/completions', payload)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return asdict(self.usage_stats)
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = APIUsageStats()
        logger.info("API usage statistics reset")

class DeepSeekAnalyzer:
    """
    Main DeepSeek AI Analysis Engine
    Provides comprehensive content analysis capabilities
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_client = DeepSeekAPIClient(api_key)
        self.analysis_cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache TTL

        # Analysis prompts
        self.prompts = self._load_analysis_prompts()

        logger.info("DeepSeek Analyzer initialized")

    def _load_analysis_prompts(self) -> Dict[str, str]:
        """Load analysis prompts for different types of analysis"""
        return {
            'sentiment': """
            Analyze the sentiment of the following social media content.
            Provide a detailed sentiment analysis including:
            1. Overall sentiment (positive, negative, neutral) with confidence score (0-1)
            2. Emotional tone (joy, anger, sadness, fear, surprise, disgust, trust, anticipation)
            3. Intensity level (low, medium, high)
            4. Key phrases that indicate sentiment
            5. Context considerations

            Content: {content}

            Respond in JSON format:
            {{
                "sentiment": "positive|negative|neutral",
                "confidence": 0.85,
                "emotions": {{"joy": 0.7, "trust": 0.6, ...}},
                "intensity": "medium",
                "key_phrases": ["phrase1", "phrase2"],
                "reasoning": "explanation of analysis"
            }}
            """,

            'topics': """
            Extract and categorize the main topics from this social media content.
            Identify:
            1. Primary topics (most important themes)
            2. Secondary topics (supporting themes)
            3. Categories (lifestyle, business, entertainment, etc.)
            4. Keywords and key phrases
            5. Hashtag relevance
            6. Brand mentions

            Content: {content}

            Respond in JSON format:
            {{
                "primary_topics": ["topic1", "topic2"],
                "secondary_topics": ["topic3", "topic4"],
                "categories": ["category1", "category2"],
                "keywords": ["keyword1", "keyword2"],
                "brand_mentions": ["brand1", "brand2"],
                "confidence": 0.9
            }}
            """,

            'engagement_prediction': """
            Predict the engagement potential of this social media content.
            Consider:
            1. Content quality and appeal
            2. Timing and relevance
            3. Hashtag effectiveness
            4. Visual appeal (if applicable)
            5. Call-to-action presence
            6. Trending topics alignment

            Content: {content}
            Additional context: {context}

            Respond in JSON format:
            {{
                "engagement_score": 0.75,
                "predicted_likes": 150,
                "predicted_comments": 25,
                "predicted_shares": 10,
                "factors": {{"content_quality": 0.8, "timing": 0.7, ...}},
                "recommendations": ["suggestion1", "suggestion2"]
            }}
            """,

            'bot_detection': """
            Analyze this user profile data to determine the likelihood of it being a bot account.
            Consider:
            1. Profile completeness and authenticity
            2. Posting patterns and frequency
            3. Engagement patterns
            4. Follower/following ratios
            5. Content quality and originality
            6. Account age and activity history

            Profile data: {profile_data}

            Respond in JSON format:
            {{
                "bot_probability": 0.25,
                "confidence": 0.85,
                "indicators": {{"suspicious_patterns": ["pattern1"], "authentic_signals": ["signal1"]}},
                "risk_level": "low|medium|high",
                "reasoning": "detailed explanation"
            }}
            """,

            'behavioral_analysis': """
            Analyze behavioral patterns in this social media activity data.
            Look for:
            1. Posting frequency patterns
            2. Content style consistency
            3. Engagement timing patterns
            4. Topic preferences and shifts
            5. Interaction behaviors
            6. Anomalies or unusual patterns

            Activity data: {activity_data}

            Respond in JSON format:
            {{
                "patterns": {{"posting_frequency": "consistent", "content_style": "varied", ...}},
                "anomalies": ["anomaly1", "anomaly2"],
                "trends": ["trend1", "trend2"],
                "behavioral_score": 0.8,
                "insights": ["insight1", "insight2"]
            }}
            """,

            'influence_scoring': """
            Calculate an influence score for this social media profile.
            Consider:
            1. Follower count and quality
            2. Engagement rates and authenticity
            3. Content reach and virality
            4. Network connections and mentions
            5. Brand partnerships and collaborations
            6. Thought leadership indicators

            Profile data: {profile_data}
            Engagement data: {engagement_data}

            Respond in JSON format:
            {{
                "influence_score": 7.5,
                "category": "micro-influencer|macro-influencer|celebrity|regular",
                "strengths": ["strength1", "strength2"],
                "growth_potential": 0.8,
                "audience_quality": 0.9,
                "niche_authority": 0.7
            }}
            """
        }

    def _generate_cache_key(self, content: str, analysis_type: AnalysisType) -> str:
        """Generate cache key for analysis results"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{analysis_type.value}_{content_hash}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if 'timestamp' not in cache_entry:
            return False

        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        return (datetime.now(timezone.utc) - cache_time).seconds < self.cache_ttl

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from AI, handling potential formatting issues"""
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find JSON-like content
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Fallback: return error structure
            logger.error(f"Failed to parse JSON response: {response_text}")
            return {
                "error": "Failed to parse AI response",
                "raw_response": response_text,
                "confidence": 0.0
            }

    def analyze_sentiment(self, content: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze sentiment of social media content

        Args:
            content: Text content to analyze
            context: Additional context information

        Returns:
            AnalysisResult with sentiment analysis
        """
        start_time = time.time()

        # Check cache first
        cache_key = self._generate_cache_key(content, AnalysisType.SENTIMENT)
        if cache_key in self.analysis_cache and self._is_cache_valid(self.analysis_cache[cache_key]):
            cached_result = self.analysis_cache[cache_key]
            logger.debug("Returning cached sentiment analysis")
            return AnalysisResult(
                analysis_type=AnalysisType.SENTIMENT,
                confidence=cached_result['confidence'],
                result=cached_result['result'],
                metadata=cached_result['metadata'],
                timestamp=datetime.fromisoformat(cached_result['timestamp']),
                processing_time=cached_result['processing_time']
            )

        try:
            # Prepare prompt
            prompt = self.prompts['sentiment'].format(content=content)

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert social media analyst specializing in sentiment analysis."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.SENTIMENT,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'content_length': len(content),
                    'model_used': config.deepseek.model_chat,
                    'context': context or {}
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            # Cache result
            self.analysis_cache[cache_key] = result.to_dict()

            logger.info(f"Sentiment analysis completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.SENTIMENT,
                confidence=0.0,
                result={"error": str(e), "sentiment": "neutral"},
                metadata={"error": True, "content_length": len(content)},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def analyze_topics(self, content: str, context: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Extract and categorize topics from content

        Args:
            content: Text content to analyze
            context: Additional context information

        Returns:
            AnalysisResult with topic analysis
        """
        start_time = time.time()

        # Check cache first
        cache_key = self._generate_cache_key(content, AnalysisType.TOPICS)
        if cache_key in self.analysis_cache and self._is_cache_valid(self.analysis_cache[cache_key]):
            cached_result = self.analysis_cache[cache_key]
            logger.debug("Returning cached topic analysis")
            return AnalysisResult(
                analysis_type=AnalysisType.TOPICS,
                confidence=cached_result['confidence'],
                result=cached_result['result'],
                metadata=cached_result['metadata'],
                timestamp=datetime.fromisoformat(cached_result['timestamp']),
                processing_time=cached_result['processing_time']
            )

        try:
            # Prepare prompt
            prompt = self.prompts['topics'].format(content=content)

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert content analyst specializing in topic extraction and categorization."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.TOPICS,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'content_length': len(content),
                    'model_used': config.deepseek.model_chat,
                    'context': context or {}
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            # Cache result
            self.analysis_cache[cache_key] = result.to_dict()

            logger.info(f"Topic analysis completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Topic analysis failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.TOPICS,
                confidence=0.0,
                result={"error": str(e), "primary_topics": [], "secondary_topics": []},
                metadata={"error": True, "content_length": len(content)},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def predict_engagement(self, content: str, context: Dict[str, Any]) -> AnalysisResult:
        """
        Predict engagement potential for content

        Args:
            content: Text content to analyze
            context: Context including follower count, posting time, etc.

        Returns:
            AnalysisResult with engagement prediction
        """
        start_time = time.time()

        try:
            # Prepare prompt with context
            prompt = self.prompts['engagement_prediction'].format(
                content=content,
                context=json.dumps(context, indent=2)
            )

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert social media strategist specializing in engagement prediction."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.ENGAGEMENT_PREDICTION,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'content_length': len(content),
                    'model_used': config.deepseek.model_chat,
                    'context': context
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            logger.info(f"Engagement prediction completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Engagement prediction failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.ENGAGEMENT_PREDICTION,
                confidence=0.0,
                result={"error": str(e), "engagement_score": 0.5},
                metadata={"error": True, "content_length": len(content)},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def detect_bot_probability(self, profile_data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze profile to detect bot probability

        Args:
            profile_data: Dictionary containing profile information

        Returns:
            AnalysisResult with bot detection analysis
        """
        start_time = time.time()

        try:
            # Prepare prompt
            prompt = self.prompts['bot_detection'].format(
                profile_data=json.dumps(profile_data, indent=2)
            )

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert in social media bot detection and account authenticity analysis."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.BOT_DETECTION,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'profile_username': profile_data.get('username', 'unknown'),
                    'model_used': config.deepseek.model_chat,
                    'analysis_factors': list(profile_data.keys())
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            logger.info(f"Bot detection completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Bot detection failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.BOT_DETECTION,
                confidence=0.0,
                result={"error": str(e), "bot_probability": 0.5, "risk_level": "unknown"},
                metadata={"error": True, "profile_username": profile_data.get('username', 'unknown')},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def analyze_behavioral_patterns(self, activity_data: List[Dict[str, Any]]) -> AnalysisResult:
        """
        Analyze behavioral patterns from activity data

        Args:
            activity_data: List of activity records (posts, interactions, etc.)

        Returns:
            AnalysisResult with behavioral analysis
        """
        start_time = time.time()

        try:
            # Prepare activity summary for analysis
            activity_summary = {
                'total_activities': len(activity_data),
                'date_range': self._get_date_range(activity_data),
                'activity_types': self._count_activity_types(activity_data),
                'temporal_patterns': self._analyze_temporal_patterns(activity_data),
                'sample_activities': activity_data[:10]  # First 10 for context
            }

            # Prepare prompt
            prompt = self.prompts['behavioral_analysis'].format(
                activity_data=json.dumps(activity_summary, indent=2, default=str)
            )

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert behavioral analyst specializing in social media activity patterns."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.BEHAVIORAL_ANALYSIS,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'activity_count': len(activity_data),
                    'model_used': config.deepseek.model_chat,
                    'analysis_period': activity_summary['date_range']
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            logger.info(f"Behavioral analysis completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Behavioral analysis failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.BEHAVIORAL_ANALYSIS,
                confidence=0.0,
                result={"error": str(e), "patterns": {}, "behavioral_score": 0.5},
                metadata={"error": True, "activity_count": len(activity_data)},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def calculate_influence_score(self, profile_data: Dict[str, Any], engagement_data: Dict[str, Any]) -> AnalysisResult:
        """
        Calculate influence score for a profile

        Args:
            profile_data: Profile information
            engagement_data: Engagement metrics and patterns

        Returns:
            AnalysisResult with influence scoring
        """
        start_time = time.time()

        try:
            # Prepare prompt
            prompt = self.prompts['influence_scoring'].format(
                profile_data=json.dumps(profile_data, indent=2),
                engagement_data=json.dumps(engagement_data, indent=2)
            )

            # Make API request
            messages = [
                {"role": "system", "content": "You are an expert in social media influence measurement and digital marketing analytics."},
                {"role": "user", "content": prompt}
            ]

            response = self.api_client.chat_completion(messages)

            # Parse response
            ai_response = response['choices'][0]['message']['content']
            parsed_result = self._parse_json_response(ai_response)

            processing_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                analysis_type=AnalysisType.INFLUENCE_SCORING,
                confidence=parsed_result.get('confidence', 0.5),
                result=parsed_result,
                metadata={
                    'profile_username': profile_data.get('username', 'unknown'),
                    'follower_count': profile_data.get('follower_count', 0),
                    'model_used': config.deepseek.model_chat
                },
                timestamp=datetime.now(timezone.utc),
                processing_time=processing_time
            )

            logger.info(f"Influence scoring completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Influence scoring failed: {e}")
            return AnalysisResult(
                analysis_type=AnalysisType.INFLUENCE_SCORING,
                confidence=0.0,
                result={"error": str(e), "influence_score": 5.0, "category": "unknown"},
                metadata={"error": True, "profile_username": profile_data.get('username', 'unknown')},
                timestamp=datetime.now(timezone.utc),
                processing_time=time.time() - start_time
            )

    def _get_date_range(self, activity_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get date range from activity data"""
        if not activity_data:
            return {"start": "unknown", "end": "unknown"}

        dates = []
        for activity in activity_data:
            if 'timestamp' in activity:
                try:
                    if isinstance(activity['timestamp'], str):
                        dates.append(datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00')))
                    elif isinstance(activity['timestamp'], datetime):
                        dates.append(activity['timestamp'])
                except:
                    continue

        if dates:
            return {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat()
            }

        return {"start": "unknown", "end": "unknown"}

    def _count_activity_types(self, activity_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count different types of activities"""
        type_counts = Counter()
        for activity in activity_data:
            activity_type = activity.get('type', 'unknown')
            type_counts[activity_type] += 1
        return dict(type_counts)

    def _analyze_temporal_patterns(self, activity_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in activity data"""
        if not activity_data:
            return {}

        hours = []
        days_of_week = []

        for activity in activity_data:
            if 'timestamp' in activity:
                try:
                    if isinstance(activity['timestamp'], str):
                        dt = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                    elif isinstance(activity['timestamp'], datetime):
                        dt = activity['timestamp']
                    else:
                        continue

                    hours.append(dt.hour)
                    days_of_week.append(dt.weekday())
                except:
                    continue

        patterns = {}
        if hours:
            patterns['peak_hours'] = [h for h, _ in Counter(hours).most_common(3)]
            patterns['average_hour'] = statistics.mean(hours)

        if days_of_week:
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            patterns['peak_days'] = [day_names[d] for d, _ in Counter(days_of_week).most_common(3)]

        return patterns

    def analyze_post_content(self, post: Post) -> Dict[str, AnalysisResult]:
        """
        Comprehensive analysis of a single post

        Args:
            post: Post model instance

        Returns:
            Dictionary of analysis results
        """
        results = {}

        if post.caption:
            # Sentiment analysis
            results['sentiment'] = self.analyze_sentiment(
                post.caption,
                context={
                    'post_type': post.post_type,
                    'like_count': post.like_count,
                    'comment_count': post.comment_count,
                    'hashtags': post.get_hashtags_list()
                }
            )

            # Topic analysis
            results['topics'] = self.analyze_topics(
                post.caption,
                context={
                    'post_type': post.post_type,
                    'hashtags': post.get_hashtags_list(),
                    'mentions': post.get_mentions_list()
                }
            )

            # Engagement prediction
            results['engagement'] = self.predict_engagement(
                post.caption,
                context={
                    'follower_count': post.target.follower_count if post.target else 0,
                    'post_type': post.post_type,
                    'hashtags': post.get_hashtags_list(),
                    'posting_time': post.posted_at.isoformat() if post.posted_at else None
                }
            )

        return results

    def analyze_follower_profile(self, follower: Follower) -> Dict[str, AnalysisResult]:
        """
        Comprehensive analysis of a follower profile

        Args:
            follower: Follower model instance

        Returns:
            Dictionary of analysis results
        """
        results = {}

        # Prepare profile data
        profile_data = {
            'username': follower.follower_username,
            'display_name': follower.follower_display_name,
            'is_verified': follower.is_verified,
            'follower_count': follower.follower_count,
            'following_count': follower.following_count,
            'engagement_rate': follower.engagement_rate,
            'account_age_days': (datetime.now(timezone.utc) - follower.detected_at).days if follower.detected_at else None
        }

        # Bot detection
        results['bot_detection'] = self.detect_bot_probability(profile_data)

        # Influence scoring
        engagement_data = {
            'engagement_rate': follower.engagement_rate or 0,
            'follower_following_ratio': (
                follower.follower_count / max(follower.following_count, 1)
                if follower.follower_count and follower.following_count else 0
            )
        }
        results['influence'] = self.calculate_influence_score(profile_data, engagement_data)

        return results

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis engine status and statistics"""
        return {
            'api_usage': self.api_client.get_usage_stats(),
            'cache_size': len(self.analysis_cache),
            'cache_ttl': self.cache_ttl,
            'available_analyses': [analysis_type.value for analysis_type in AnalysisType],
            'status': 'operational' if self.api_client.api_key else 'no_api_key'
        }

    def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")

# Global analyzer instance
try:
    analyzer = DeepSeekAnalyzer()
except Exception as e:
    logger.warning(f"Failed to initialize global analyzer: {e}")
    analyzer = None
