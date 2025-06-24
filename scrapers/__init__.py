"""
Social Media Surveillance System - Scrapers Package
Comprehensive Instagram scraping components for surveillance and analysis.
"""

from .instagram_profile_scraper import (
    InstagramProfileScraper,
    create_profile_scraper,
    scrape_single_profile,
    scrape_profiles_batch
)

from .instagram_post_scraper import (
    InstagramPostScraper,
    create_post_scraper,
    scrape_user_posts_quick,
    scrape_recent_posts_quick
)

from .instagram_story_scraper import (
    InstagramStoryScraper,
    create_story_scraper,
    scrape_user_stories_quick
)

from .follower_tracker import (
    InstagramFollowerTracker,
    create_follower_tracker,
    track_followers_quick
)

from .instagram_hashtag_scraper import (
    InstagramHashtagScraper,
    create_hashtag_scraper,
    analyze_hashtag_quick,
    get_trending_hashtags_quick
)

from .instagram_location_scraper import (
    InstagramLocationScraper,
    create_location_scraper,
    analyze_location_quick,
    search_locations_quick,
    get_popular_locations_quick
)

__all__ = [
    # Profile scraper
    'InstagramProfileScraper',
    'create_profile_scraper',
    'scrape_single_profile',
    'scrape_profiles_batch',

    # Post scraper
    'InstagramPostScraper',
    'create_post_scraper',
    'scrape_user_posts_quick',
    'scrape_recent_posts_quick',

    # Story scraper
    'InstagramStoryScraper',
    'create_story_scraper',
    'scrape_user_stories_quick',

    # Follower tracker
    'InstagramFollowerTracker',
    'create_follower_tracker',
    'track_followers_quick',

    # Hashtag scraper
    'InstagramHashtagScraper',
    'create_hashtag_scraper',
    'analyze_hashtag_quick',
    'get_trending_hashtags_quick',

    # Location scraper
    'InstagramLocationScraper',
    'create_location_scraper',
    'analyze_location_quick',
    'search_locations_quick',
    'get_popular_locations_quick',
]