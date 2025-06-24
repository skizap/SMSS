"""
Social Media Surveillance System - Content Processing Pipeline
Advanced content preprocessing, text extraction, media analysis, and data normalization
for comprehensive social media content analysis.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import hashlib
from collections import Counter, defaultdict

import numpy as np
from PIL import Image
import requests

from models.instagram_models import Post, Story, SurveillanceTarget

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ProcessedContent:
    """Container for processed content data"""
    original_text: str
    cleaned_text: str
    hashtags: List[str]
    mentions: List[str]
    urls: List[str]
    emojis: List[str]
    language: Optional[str]
    word_count: int
    character_count: int
    readability_score: float
    sentiment_indicators: Dict[str, List[str]]
    brand_mentions: List[str]
    topics: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'original_text': self.original_text,
            'cleaned_text': self.cleaned_text,
            'hashtags': self.hashtags,
            'mentions': self.mentions,
            'urls': self.urls,
            'emojis': self.emojis,
            'language': self.language,
            'word_count': self.word_count,
            'character_count': self.character_count,
            'readability_score': self.readability_score,
            'sentiment_indicators': self.sentiment_indicators,
            'brand_mentions': self.brand_mentions,
            'topics': self.topics
        }

@dataclass
class MediaAnalysis:
    """Container for media analysis results"""
    media_type: str
    file_size: Optional[int]
    dimensions: Optional[Tuple[int, int]]
    aspect_ratio: Optional[float]
    dominant_colors: List[str]
    has_text_overlay: bool
    estimated_faces: int
    visual_complexity: float
    quality_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'media_type': self.media_type,
            'file_size': self.file_size,
            'dimensions': self.dimensions,
            'aspect_ratio': self.aspect_ratio,
            'dominant_colors': self.dominant_colors,
            'has_text_overlay': self.has_text_overlay,
            'estimated_faces': self.estimated_faces,
            'visual_complexity': self.visual_complexity,
            'quality_score': self.quality_score
        }

class TextProcessor:
    """Advanced text processing and analysis"""
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self.hashtag_pattern = re.compile(r'#[\w\u00c0-\u024f\u1e00-\u1eff]+')
        self.mention_pattern = re.compile(r'@[\w.]+')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        
        # Load brand keywords and sentiment indicators
        self.brand_keywords = self._load_brand_keywords()
        self.sentiment_keywords = self._load_sentiment_keywords()
        
        logger.info("Text processor initialized")
    
    def _load_brand_keywords(self) -> Set[str]:
        """Load common brand keywords for detection"""
        # This would typically be loaded from a configuration file or database
        return {
            'nike', 'adidas', 'apple', 'samsung', 'google', 'microsoft', 'amazon',
            'coca-cola', 'pepsi', 'mcdonalds', 'starbucks', 'netflix', 'spotify',
            'instagram', 'facebook', 'twitter', 'tiktok', 'youtube', 'linkedin',
            'tesla', 'bmw', 'mercedes', 'audi', 'toyota', 'honda', 'ford',
            'louis vuitton', 'gucci', 'prada', 'chanel', 'versace', 'armani'
        }
    
    def _load_sentiment_keywords(self) -> Dict[str, List[str]]:
        """Load sentiment indicator keywords"""
        return {
            'positive': [
                'amazing', 'awesome', 'fantastic', 'great', 'excellent', 'wonderful',
                'love', 'perfect', 'beautiful', 'incredible', 'outstanding', 'brilliant',
                'happy', 'excited', 'thrilled', 'delighted', 'pleased', 'satisfied'
            ],
            'negative': [
                'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disgusting',
                'disappointed', 'frustrated', 'angry', 'annoyed', 'upset', 'sad',
                'boring', 'useless', 'worthless', 'pathetic', 'ridiculous', 'stupid'
            ],
            'neutral': [
                'okay', 'fine', 'average', 'normal', 'standard', 'typical', 'regular',
                'usual', 'common', 'ordinary', 'moderate', 'fair', 'decent'
            ]
        }
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        hashtags = self.hashtag_pattern.findall(text)
        return [tag.lower() for tag in hashtags]
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract user mentions from text"""
        mentions = self.mention_pattern.findall(text)
        return [mention.lower() for mention in mentions]
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        return self.url_pattern.findall(text)
    
    def extract_emojis(self, text: str) -> List[str]:
        """Extract emojis from text"""
        return self.emoji_pattern.findall(text)
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing URLs, mentions, hashtags, and extra whitespace"""
        # Remove URLs
        cleaned = self.url_pattern.sub('', text)
        
        # Remove mentions and hashtags
        cleaned = self.mention_pattern.sub('', cleaned)
        cleaned = self.hashtag_pattern.sub('', cleaned)
        
        # Remove emojis
        cleaned = self.emoji_pattern.sub('', cleaned)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def detect_language(self, text: str) -> Optional[str]:
        """Simple language detection based on character patterns"""
        if not text:
            return None
        
        # Simple heuristic-based language detection
        # This could be enhanced with a proper language detection library
        
        # Check for common English words
        english_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = set(text.lower().split())
        english_score = len(words.intersection(english_words)) / max(len(words), 1)
        
        if english_score > 0.1:
            return 'en'
        
        # Check for other languages based on character sets
        if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', text.lower()):
            return 'es'  # Spanish/French/Portuguese
        elif re.search(r'[äöüß]', text.lower()):
            return 'de'  # German
        elif re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'  # Chinese
        elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return 'ja'  # Japanese
        elif re.search(r'[\u0400-\u04ff]', text):
            return 'ru'  # Russian
        
        return 'unknown'
    
    def calculate_readability_score(self, text: str) -> float:
        """Calculate simple readability score (0-1, higher is more readable)"""
        if not text:
            return 0.0
        
        words = text.split()
        if not words:
            return 0.0
        
        # Simple metrics
        avg_word_length = sum(len(word) for word in words) / len(words)
        sentence_count = len(re.split(r'[.!?]+', text))
        avg_sentence_length = len(words) / max(sentence_count, 1)
        
        # Simple readability formula (inverse of complexity)
        complexity = (avg_word_length * 0.5) + (avg_sentence_length * 0.3)
        readability = max(0, min(1, 1 - (complexity / 20)))
        
        return readability
    
    def detect_sentiment_indicators(self, text: str) -> Dict[str, List[str]]:
        """Detect sentiment indicator words in text"""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        indicators = {}
        for sentiment, keywords in self.sentiment_keywords.items():
            found_keywords = [word for word in keywords if word in words]
            if found_keywords:
                indicators[sentiment] = found_keywords
        
        return indicators
    
    def detect_brand_mentions(self, text: str) -> List[str]:
        """Detect brand mentions in text"""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        found_brands = [brand for brand in self.brand_keywords if brand in words]
        return found_brands
    
    def extract_topics(self, text: str) -> List[str]:
        """Extract potential topics from text using keyword analysis"""
        if not text:
            return []
        
        # Clean text and get words
        cleaned = self.clean_text(text).lower()
        words = re.findall(r'\b\w{3,}\b', cleaned)  # Words with 3+ characters
        
        # Count word frequency
        word_counts = Counter(words)
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'shall', 'not'
        }
        
        # Get most common non-stop words as topics
        topics = [word for word, count in word_counts.most_common(10) 
                 if word not in stop_words and count > 1]
        
        return topics[:5]  # Return top 5 topics

    def process_text(self, text: str) -> ProcessedContent:
        """
        Comprehensive text processing and analysis

        Args:
            text: Raw text content to process

        Returns:
            ProcessedContent with all extracted information
        """
        if not text:
            return ProcessedContent(
                original_text="",
                cleaned_text="",
                hashtags=[],
                mentions=[],
                urls=[],
                emojis=[],
                language=None,
                word_count=0,
                character_count=0,
                readability_score=0.0,
                sentiment_indicators={},
                brand_mentions=[],
                topics=[]
            )

        # Extract all components
        hashtags = self.extract_hashtags(text)
        mentions = self.extract_mentions(text)
        urls = self.extract_urls(text)
        emojis = self.extract_emojis(text)
        cleaned_text = self.clean_text(text)

        # Analyze text properties
        language = self.detect_language(cleaned_text)
        word_count = len(cleaned_text.split()) if cleaned_text else 0
        character_count = len(text)
        readability_score = self.calculate_readability_score(cleaned_text)

        # Extract semantic information
        sentiment_indicators = self.detect_sentiment_indicators(text)
        brand_mentions = self.detect_brand_mentions(text)
        topics = self.extract_topics(text)

        return ProcessedContent(
            original_text=text,
            cleaned_text=cleaned_text,
            hashtags=hashtags,
            mentions=mentions,
            urls=urls,
            emojis=emojis,
            language=language,
            word_count=word_count,
            character_count=character_count,
            readability_score=readability_score,
            sentiment_indicators=sentiment_indicators,
            brand_mentions=brand_mentions,
            topics=topics
        )

class MediaProcessor:
    """Advanced media analysis and processing"""

    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi'}
        logger.info("Media processor initialized")

    def analyze_image(self, image_path: str) -> MediaAnalysis:
        """
        Analyze image properties and content

        Args:
            image_path: Path to image file or URL

        Returns:
            MediaAnalysis with image analysis results
        """
        try:
            # Load image
            if image_path.startswith('http'):
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()
                from io import BytesIO
                image = Image.open(BytesIO(response.content))
                file_size = len(response.content)
            else:
                image = Image.open(image_path)
                import os
                file_size = os.path.getsize(image_path) if os.path.exists(image_path) else None

            # Basic properties
            width, height = image.size
            aspect_ratio = width / height if height > 0 else 1.0

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Analyze colors
            dominant_colors = self._extract_dominant_colors(image)

            # Estimate visual complexity
            visual_complexity = self._calculate_visual_complexity(image)

            # Estimate quality
            quality_score = self._estimate_image_quality(image)

            # Simple text overlay detection (based on edge density)
            has_text_overlay = self._detect_text_overlay(image)

            # Simple face detection (placeholder - would use proper face detection)
            estimated_faces = self._estimate_faces(image)

            return MediaAnalysis(
                media_type='image',
                file_size=file_size,
                dimensions=(width, height),
                aspect_ratio=aspect_ratio,
                dominant_colors=dominant_colors,
                has_text_overlay=has_text_overlay,
                estimated_faces=estimated_faces,
                visual_complexity=visual_complexity,
                quality_score=quality_score
            )

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return MediaAnalysis(
                media_type='image',
                file_size=None,
                dimensions=None,
                aspect_ratio=None,
                dominant_colors=[],
                has_text_overlay=False,
                estimated_faces=0,
                visual_complexity=0.0,
                quality_score=0.0
            )

    def _extract_dominant_colors(self, image: Image.Image, num_colors: int = 5) -> List[str]:
        """Extract dominant colors from image"""
        try:
            # Resize image for faster processing
            image_small = image.resize((150, 150))

            # Convert to numpy array
            pixels = np.array(image_small)
            pixels = pixels.reshape(-1, 3)

            # Simple color clustering (k-means would be better)
            from collections import Counter

            # Quantize colors to reduce complexity
            quantized = (pixels // 32) * 32

            # Count color frequencies
            color_counts = Counter(map(tuple, quantized))

            # Get most common colors
            dominant = color_counts.most_common(num_colors)

            # Convert to hex strings
            hex_colors = []
            for (r, g, b), _ in dominant:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                hex_colors.append(hex_color)

            return hex_colors

        except Exception as e:
            logger.error(f"Color extraction failed: {e}")
            return []

    def _calculate_visual_complexity(self, image: Image.Image) -> float:
        """Calculate visual complexity score (0-1)"""
        try:
            # Convert to grayscale
            gray = image.convert('L')
            gray_small = gray.resize((100, 100))

            # Convert to numpy array
            pixels = np.array(gray_small, dtype=np.float32)

            # Calculate gradient magnitude (edge density)
            grad_x = np.abs(np.diff(pixels, axis=1))
            grad_y = np.abs(np.diff(pixels, axis=0))

            # Average gradient magnitude
            edge_density = (np.mean(grad_x) + np.mean(grad_y)) / 2

            # Normalize to 0-1 range
            complexity = min(1.0, edge_density / 50.0)

            return complexity

        except Exception as e:
            logger.error(f"Visual complexity calculation failed: {e}")
            return 0.0

    def _estimate_image_quality(self, image: Image.Image) -> float:
        """Estimate image quality score (0-1)"""
        try:
            width, height = image.size

            # Resolution score
            resolution_score = min(1.0, (width * height) / (1920 * 1080))

            # Aspect ratio score (closer to common ratios is better)
            aspect_ratio = width / height
            common_ratios = [16/9, 4/3, 1/1, 3/4, 9/16]
            aspect_score = max([1 - abs(aspect_ratio - ratio) for ratio in common_ratios])
            aspect_score = max(0, min(1, aspect_score))

            # Simple sharpness estimation
            gray = image.convert('L').resize((200, 200))
            pixels = np.array(gray, dtype=np.float32)
            laplacian_var = np.var(np.gradient(pixels))
            sharpness_score = min(1.0, laplacian_var / 1000.0)

            # Combined quality score
            quality = (resolution_score * 0.4 + aspect_score * 0.3 + sharpness_score * 0.3)

            return quality

        except Exception as e:
            logger.error(f"Quality estimation failed: {e}")
            return 0.5

    def _detect_text_overlay(self, image: Image.Image) -> bool:
        """Simple text overlay detection based on edge patterns"""
        try:
            # Convert to grayscale and resize
            gray = image.convert('L').resize((200, 200))
            pixels = np.array(gray)

            # Calculate horizontal and vertical edge densities
            h_edges = np.abs(np.diff(pixels, axis=1))
            v_edges = np.abs(np.diff(pixels, axis=0))

            # Text typically has high horizontal edge density
            h_density = np.mean(h_edges)
            v_density = np.mean(v_edges)

            # Simple heuristic: text overlay likely if high horizontal edges
            return h_density > 20 and h_density > v_density * 1.2

        except Exception as e:
            logger.error(f"Text overlay detection failed: {e}")
            return False

    def _estimate_faces(self, image: Image.Image) -> int:
        """Simple face estimation (placeholder for proper face detection)"""
        try:
            # This is a very simple heuristic - in production, use proper face detection
            width, height = image.size

            # Assume faces are more likely in certain aspect ratios and sizes
            aspect_ratio = width / height

            # Portrait-like images more likely to have faces
            if 0.7 <= aspect_ratio <= 1.3 and width >= 200 and height >= 200:
                return 1
            elif aspect_ratio > 1.5 and width >= 400:  # Landscape might have multiple faces
                return 2

            return 0

        except Exception as e:
            logger.error(f"Face estimation failed: {e}")
            return 0

class ContentProcessor:
    """
    Main content processing pipeline that combines text and media analysis
    """

    def __init__(self):
        self.text_processor = TextProcessor()
        self.media_processor = MediaProcessor()
        logger.info("Content processor initialized")

    def process_post(self, post: Post) -> Dict[str, Any]:
        """
        Process a complete post including text and media

        Args:
            post: Post model instance

        Returns:
            Dictionary with comprehensive processing results
        """
        results = {
            'post_id': post.id,
            'instagram_post_id': post.instagram_post_id,
            'post_type': post.post_type,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }

        # Process text content
        if post.caption:
            text_analysis = self.text_processor.process_text(post.caption)
            results['text_analysis'] = text_analysis.to_dict()
        else:
            results['text_analysis'] = None

        # Process media content
        media_analyses = []
        if post.media_urls:
            for media_url in post.media_urls:
                if isinstance(media_url, str):
                    media_analysis = self.media_processor.analyze_image(media_url)
                    media_analyses.append(media_analysis.to_dict())

        results['media_analyses'] = media_analyses

        # Generate content summary
        results['content_summary'] = self._generate_content_summary(results)

        return results

    def process_story(self, story: Story) -> Dict[str, Any]:
        """
        Process a story including text and media

        Args:
            story: Story model instance

        Returns:
            Dictionary with processing results
        """
        results = {
            'story_id': story.id,
            'instagram_story_id': story.story_id,
            'media_type': story.media_type,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }

        # Process text content
        if story.story_text:
            text_analysis = self.text_processor.process_text(story.story_text)
            results['text_analysis'] = text_analysis.to_dict()
        else:
            results['text_analysis'] = None

        # Process media content
        if story.media_url:
            if story.media_type == 'photo':
                media_analysis = self.media_processor.analyze_image(story.media_url)
                results['media_analysis'] = media_analysis.to_dict()
            else:
                # For videos, we'd need video analysis (placeholder)
                results['media_analysis'] = {
                    'media_type': 'video',
                    'analysis': 'video_analysis_not_implemented'
                }

        # Generate content summary
        results['content_summary'] = self._generate_content_summary(results)

        return results

    def process_profile_content(self, target: SurveillanceTarget) -> Dict[str, Any]:
        """
        Process profile content including bio and other text

        Args:
            target: SurveillanceTarget model instance

        Returns:
            Dictionary with profile content analysis
        """
        results = {
            'target_id': target.id,
            'username': target.instagram_username,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }

        # Process bio
        if target.bio:
            bio_analysis = self.text_processor.process_text(target.bio)
            results['bio_analysis'] = bio_analysis.to_dict()
        else:
            results['bio_analysis'] = None

        # Analyze profile completeness
        results['profile_completeness'] = self._analyze_profile_completeness(target)

        return results

    def _generate_content_summary(self, processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of content processing results"""
        summary = {
            'has_text': processing_results.get('text_analysis') is not None,
            'has_media': bool(processing_results.get('media_analyses') or processing_results.get('media_analysis')),
            'content_quality_score': 0.0,
            'engagement_indicators': []
        }

        # Calculate content quality score
        quality_factors = []

        # Text quality factors
        text_analysis = processing_results.get('text_analysis')
        if text_analysis:
            quality_factors.append(text_analysis['readability_score'])

            # Bonus for hashtags and mentions
            if text_analysis['hashtags']:
                quality_factors.append(0.8)
            if text_analysis['mentions']:
                quality_factors.append(0.7)

            # Engagement indicators
            if text_analysis['sentiment_indicators']:
                summary['engagement_indicators'].append('sentiment_words')
            if text_analysis['brand_mentions']:
                summary['engagement_indicators'].append('brand_mentions')
            if len(text_analysis['hashtags']) > 0:
                summary['engagement_indicators'].append('hashtags')

        # Media quality factors
        media_analyses = processing_results.get('media_analyses', [])
        if media_analyses:
            media_quality_scores = [ma.get('quality_score', 0) for ma in media_analyses if ma.get('quality_score')]
            if media_quality_scores:
                quality_factors.extend(media_quality_scores)
                summary['engagement_indicators'].append('visual_content')

        # Calculate overall quality score
        if quality_factors:
            summary['content_quality_score'] = sum(quality_factors) / len(quality_factors)

        return summary

    def _analyze_profile_completeness(self, target: SurveillanceTarget) -> Dict[str, Any]:
        """Analyze how complete a profile is"""
        completeness_factors = {
            'has_bio': bool(target.bio),
            'has_external_url': bool(target.external_url),
            'has_profile_pic': bool(target.profile_pic_url),
            'is_verified': target.is_verified,
            'has_posts': target.post_count > 0,
            'has_followers': target.follower_count > 0
        }

        # Calculate completeness score
        completed_factors = sum(1 for factor in completeness_factors.values() if factor)
        total_factors = len(completeness_factors)
        completeness_score = completed_factors / total_factors

        return {
            'factors': completeness_factors,
            'completeness_score': completeness_score,
            'missing_elements': [
                factor for factor, completed in completeness_factors.items()
                if not completed
            ]
        }

    def batch_process_posts(self, posts: List[Post]) -> List[Dict[str, Any]]:
        """
        Process multiple posts in batch

        Args:
            posts: List of Post model instances

        Returns:
            List of processing results
        """
        results = []

        for post in posts:
            try:
                result = self.process_post(post)
                results.append(result)
                logger.debug(f"Processed post {post.instagram_post_id}")
            except Exception as e:
                logger.error(f"Failed to process post {post.instagram_post_id}: {e}")
                results.append({
                    'post_id': post.id,
                    'instagram_post_id': post.instagram_post_id,
                    'error': str(e),
                    'processed_at': datetime.now(timezone.utc).isoformat()
                })

        logger.info(f"Batch processed {len(results)} posts")
        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and status"""
        return {
            'text_processor_status': 'operational',
            'media_processor_status': 'operational',
            'supported_media_formats': list(self.media_processor.supported_formats),
            'brand_keywords_count': len(self.text_processor.brand_keywords),
            'sentiment_keywords_count': sum(
                len(keywords) for keywords in self.text_processor.sentiment_keywords.values()
            )
        }

# Global content processor instance
content_processor = ContentProcessor()
