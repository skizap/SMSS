"""
Social Media Surveillance System - Phase 4 Analysis Testing Suite
Comprehensive tests for the AI analysis engine, including unit tests,
integration tests, and mock API response validation.
"""

import unittest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import analysis modules
from analysis.deepseek_analyzer import (
    DeepSeekAPIClient, DeepSeekAnalyzer, AnalysisType, AnalysisResult
)
from analysis.content_processor import (
    TextProcessor, MediaProcessor, ContentProcessor, ProcessedContent
)
from analysis.pattern_detector import (
    FollowerPatternAnalyzer, ContentPatternAnalyzer, AnomalyDetector, PatternDetector
)
from analysis.analysis_database import AnalysisDatabaseManager
from analysis.error_handler import AnalysisErrorHandler, ErrorCategory, ErrorSeverity

class TestDeepSeekAnalyzer(unittest.TestCase):
    """Test DeepSeek AI analyzer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_api_key = "test_api_key_12345"
        
    @patch('analysis.deepseek_analyzer.requests.Session')
    def test_api_client_initialization(self, mock_session):
        """Test API client initialization"""
        client = DeepSeekAPIClient(self.mock_api_key)
        
        self.assertEqual(client.api_key, self.mock_api_key)
        self.assertEqual(client.base_url, "https://api.deepseek.com/v1")
        self.assertIsNotNone(client.session)
        
    @patch('analysis.deepseek_analyzer.requests.Session.post')
    def test_successful_api_request(self, mock_post):
        """Test successful API request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"sentiment": "positive", "confidence": 0.9}'}}],
            'usage': {'total_tokens': 150}
        }
        mock_post.return_value = mock_response
        
        client = DeepSeekAPIClient(self.mock_api_key)
        
        messages = [{"role": "user", "content": "Test message"}]
        result = client.chat_completion(messages)
        
        self.assertIn('choices', result)
        self.assertEqual(client.usage_stats.successful_requests, 1)
        
    @patch('analysis.deepseek_analyzer.requests.Session.post')
    def test_rate_limit_handling(self, mock_post):
        """Test rate limit handling"""
        # Mock rate limit response followed by success
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}  # Short delay for testing

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            'choices': [{'message': {'content': 'test response'}}],
            'usage': {'total_tokens': 10}
        }

        # First call returns rate limit, second call succeeds
        mock_post.side_effect = [rate_limit_response, success_response]

        client = DeepSeekAPIClient(self.mock_api_key)

        # Should succeed after retry
        result = client.chat_completion([{"role": "user", "content": "Test"}])

        self.assertIn('choices', result)
        self.assertEqual(client.usage_stats.rate_limit_hits, 1)
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis functionality"""
        with patch.object(DeepSeekAPIClient, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                'choices': [{'message': {'content': '{"sentiment": "positive", "confidence": 0.85, "emotions": {"joy": 0.7}}'}}]
            }
            
            analyzer = DeepSeekAnalyzer(self.mock_api_key)
            result = analyzer.analyze_sentiment("I love this amazing product!")
            
            self.assertEqual(result.analysis_type, AnalysisType.SENTIMENT)
            self.assertGreater(result.confidence, 0.8)
            self.assertIn('sentiment', result.result)
    
    def test_topic_analysis(self):
        """Test topic analysis functionality"""
        with patch.object(DeepSeekAPIClient, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                'choices': [{'message': {'content': '{"primary_topics": ["technology", "innovation"], "confidence": 0.9}'}}]
            }
            
            analyzer = DeepSeekAnalyzer(self.mock_api_key)
            result = analyzer.analyze_topics("Latest technology innovations are amazing")
            
            self.assertEqual(result.analysis_type, AnalysisType.TOPICS)
            self.assertIn('primary_topics', result.result)
    
    def test_bot_detection(self):
        """Test bot detection functionality"""
        with patch.object(DeepSeekAPIClient, 'chat_completion') as mock_chat:
            mock_chat.return_value = {
                'choices': [{'message': {'content': '{"bot_probability": 0.3, "confidence": 0.8, "risk_level": "low"}'}}]
            }
            
            analyzer = DeepSeekAnalyzer(self.mock_api_key)
            profile_data = {
                'username': 'test_user',
                'follower_count': 1000,
                'following_count': 500,
                'is_verified': False
            }
            
            result = analyzer.detect_bot_probability(profile_data)
            
            self.assertEqual(result.analysis_type, AnalysisType.BOT_DETECTION)
            self.assertIn('bot_probability', result.result)

class TestContentProcessor(unittest.TestCase):
    """Test content processing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.text_processor = TextProcessor()
        self.content_processor = ContentProcessor()
        
    def test_hashtag_extraction(self):
        """Test hashtag extraction"""
        text = "Love this #amazing #product #tech"
        hashtags = self.text_processor.extract_hashtags(text)
        
        expected = ['#amazing', '#product', '#tech']
        self.assertEqual(hashtags, expected)
    
    def test_mention_extraction(self):
        """Test mention extraction"""
        text = "Thanks @user1 and @user2 for the recommendation"
        mentions = self.text_processor.extract_mentions(text)
        
        expected = ['@user1', '@user2']
        self.assertEqual(mentions, expected)
    
    def test_url_extraction(self):
        """Test URL extraction"""
        text = "Check out https://example.com and http://test.org"
        urls = self.text_processor.extract_urls(text)
        
        self.assertEqual(len(urls), 2)
        self.assertIn('https://example.com', urls)
        self.assertIn('http://test.org', urls)
    
    def test_text_cleaning(self):
        """Test text cleaning"""
        text = "Check out https://example.com @user #hashtag 🎉"
        cleaned = self.text_processor.clean_text(text)
        
        # Should remove URLs, mentions, hashtags, and emojis
        self.assertNotIn('https://example.com', cleaned)
        self.assertNotIn('@user', cleaned)
        self.assertNotIn('#hashtag', cleaned)
        self.assertNotIn('🎉', cleaned)
        self.assertIn('Check out', cleaned)
    
    def test_language_detection(self):
        """Test language detection"""
        english_text = "This is a test message in English"
        language = self.text_processor.detect_language(english_text)
        
        self.assertEqual(language, 'en')
    
    def test_readability_score(self):
        """Test readability score calculation"""
        simple_text = "This is simple. Easy to read."
        complex_text = "Extraordinarily sophisticated terminology demonstrates incomprehensible complexity."
        
        simple_score = self.text_processor.calculate_readability_score(simple_text)
        complex_score = self.text_processor.calculate_readability_score(complex_text)
        
        self.assertGreater(simple_score, complex_score)
    
    def test_brand_mention_detection(self):
        """Test brand mention detection"""
        text = "I love my new Nike shoes and Apple iPhone"
        brands = self.text_processor.detect_brand_mentions(text)
        
        self.assertIn('nike', brands)
        self.assertIn('apple', brands)
    
    def test_comprehensive_text_processing(self):
        """Test comprehensive text processing"""
        text = "Amazing #product from @brand! Check https://example.com 🎉"
        
        processed = self.text_processor.process_text(text)
        
        self.assertIsInstance(processed, ProcessedContent)
        self.assertEqual(processed.original_text, text)
        self.assertGreater(processed.word_count, 0)
        self.assertGreater(processed.character_count, 0)
        self.assertEqual(len(processed.hashtags), 1)
        self.assertEqual(len(processed.mentions), 1)
        self.assertEqual(len(processed.urls), 1)

class TestPatternDetector(unittest.TestCase):
    """Test pattern detection functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.pattern_detector = PatternDetector()
        
    def test_follower_pattern_analyzer_initialization(self):
        """Test follower pattern analyzer initialization"""
        analyzer = FollowerPatternAnalyzer()
        self.assertIsNotNone(analyzer)
    
    def test_content_pattern_analyzer_initialization(self):
        """Test content pattern analyzer initialization"""
        analyzer = ContentPatternAnalyzer()
        self.assertIsNotNone(analyzer)
    
    def test_anomaly_detector_initialization(self):
        """Test anomaly detector initialization"""
        detector = AnomalyDetector()
        self.assertIsNotNone(detector)
    
    @patch('analysis.pattern_detector.db_manager.get_session')
    def test_pattern_detection_with_mock_data(self, mock_db_session):
        """Test pattern detection with mock database data"""
        # Mock database session and data
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        # Test pattern analysis
        result = self.pattern_detector.analyze_target_patterns(target_id=1, days=30)
        
        self.assertIsInstance(result, dict)
        self.assertIn('target_id', result)
        self.assertIn('follower_patterns', result)
        self.assertIn('content_patterns', result)
        self.assertIn('anomalies', result)

class TestAnalysisDatabase(unittest.TestCase):
    """Test analysis database functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db_manager = AnalysisDatabaseManager()
    
    @patch('analysis.analysis_database.db_manager.get_session')
    def test_save_analysis_result(self, mock_db_session):
        """Test saving analysis result"""
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock the analysis result object
        mock_result = Mock()
        mock_result.id = 123
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        
        with patch('analysis.analysis_database.AnalysisResult', return_value=mock_result):
            result_id = self.db_manager.save_analysis_result(
                target_id=1,
                content_type='post',
                content_id=100,
                analysis_type='sentiment',
                result_data={'sentiment': 'positive'},
                confidence=0.9
            )
            
            self.assertEqual(result_id, 123)
    
    @patch('analysis.analysis_database.db_manager.get_session')
    def test_get_analysis_results(self, mock_db_session):
        """Test retrieving analysis results"""
        mock_session = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        results = self.db_manager.get_analysis_results(target_id=1, analysis_type='sentiment')
        
        self.assertIsInstance(results, list)

class TestErrorHandler(unittest.TestCase):
    """Test error handling functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = AnalysisErrorHandler()
    
    def test_error_handling(self):
        """Test basic error handling"""
        test_error = ValueError("Test error message")
        
        error_info = self.error_handler.handle_error(
            test_error,
            ErrorCategory.PROCESSING_ERROR,
            ErrorSeverity.MEDIUM,
            context={'test': True}
        )
        
        self.assertIsNotNone(error_info.error_id)
        self.assertEqual(error_info.category, ErrorCategory.PROCESSING_ERROR)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error_info.message, "Test error message")
    
    def test_retry_mechanism(self):
        """Test retry mechanism"""
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = self.error_handler.retry_with_backoff(
            failing_function,
            ErrorCategory.API_ERROR
        )
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_fallback_strategy(self):
        """Test fallback strategy"""
        def failing_function():
            raise ValueError("Function failed")
        
        result = self.error_handler.execute_with_fallback(
            failing_function,
            ErrorCategory.PROCESSING_ERROR,
            fallback_result="fallback_value"
        )
        
        self.assertEqual(result, "fallback_value")
    
    def test_error_statistics(self):
        """Test error statistics"""
        # Generate some test errors
        for i in range(5):
            self.error_handler.handle_error(
                ValueError(f"Test error {i}"),
                ErrorCategory.PROCESSING_ERROR,
                ErrorSeverity.LOW
            )
        
        stats = self.error_handler.get_error_statistics()
        
        self.assertEqual(stats['total_errors'], 5)
        self.assertIn('category_breakdown', stats)
        self.assertIn('severity_breakdown', stats)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete analysis system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_api_key = "test_integration_key"
    
    @patch('analysis.deepseek_analyzer.requests.Session.post')
    def test_end_to_end_content_analysis(self, mock_post):
        """Test end-to-end content analysis workflow"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"sentiment": "positive", "confidence": 0.9, "topics": ["technology"]}'}}],
            'usage': {'total_tokens': 100}
        }
        mock_post.return_value = mock_response
        
        # Create analyzer
        analyzer = DeepSeekAnalyzer(self.mock_api_key)
        
        # Test content
        test_content = "I love this amazing new #technology! @company did great work 🎉"
        
        # Perform analysis
        sentiment_result = analyzer.analyze_sentiment(test_content)
        topic_result = analyzer.analyze_topics(test_content)
        
        # Verify results
        self.assertEqual(sentiment_result.analysis_type, AnalysisType.SENTIMENT)
        self.assertEqual(topic_result.analysis_type, AnalysisType.TOPICS)
        self.assertGreater(sentiment_result.confidence, 0.8)
    
    def test_content_processing_pipeline(self):
        """Test complete content processing pipeline"""
        processor = ContentProcessor()
        
        # Mock post object
        mock_post = Mock()
        mock_post.id = 1
        mock_post.instagram_post_id = "test_post_123"
        mock_post.post_type = "photo"
        mock_post.caption = "Amazing #sunset photo! Thanks @photographer 📸"
        mock_post.media_urls = []
        
        # Process post
        result = processor.process_post(mock_post)
        
        # Verify processing results
        self.assertIn('post_id', result)
        self.assertIn('text_analysis', result)
        self.assertIn('content_summary', result)
        
        if result['text_analysis']:
            self.assertIn('hashtags', result['text_analysis'])
            self.assertIn('mentions', result['text_analysis'])

def run_analysis_tests():
    """Run all analysis tests"""
    print("🧪 Running Phase 4 Analysis Engine Tests...")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDeepSeekAnalyzer,
        TestContentProcessor,
        TestPatternDetector,
        TestAnalysisDatabase,
        TestErrorHandler,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n🚨 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n✅ All tests passed successfully!")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_analysis_tests()
    exit(0 if success else 1)
