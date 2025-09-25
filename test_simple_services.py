#!/usr/bin/env python3
"""
Simplified test for individual services.
Tests Writer and Presenter services directly.
"""

import asyncio
import json
import logging
import requests
import time
from typing import Dict, Any, List
from uuid import UUID, uuid4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleServiceTester:
    """Test individual services directly."""
    
    def __init__(self):
        self.session = requests.Session()
    
    def test_writer_service(self):
        """Test the writer service directly."""
        logger.info("✍️ Testing Writer Service...")
        
        # Test health
        try:
            response = self.session.get("http://localhost:8003/health")
            if response.status_code == 200:
                logger.info("✅ Writer service is healthy")
            else:
                logger.error(f"❌ Writer service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to writer service: {e}")
            return False
        
        # Test metadata generation
        test_script = """
        Welcome to AI Weekly, your source for the latest developments in artificial intelligence and machine learning. 
        I'm Alex Chen, and today we're diving deep into the fascinating world of large language models and their impact on various industries.
        
        In recent news, we've seen remarkable advances in AI technology that are reshaping how we think about human-computer interaction. 
        From GPT models that can engage in natural conversations to specialized AI systems that can write code, create art, and even assist in scientific research, 
        the pace of innovation continues to accelerate.
        
        One of the most exciting developments this week has been the release of new multimodal AI systems that can process both text and images simultaneously. 
        These systems represent a significant leap forward in AI capabilities, enabling more sophisticated understanding of complex, real-world scenarios.
        
        The implications for businesses are profound. Companies across industries are now exploring how to integrate these advanced AI systems into their workflows. 
        From customer service automation to content creation, from data analysis to creative design, AI is becoming an indispensable tool for modern enterprises.
        
        However, with these advances come important considerations about ethics, privacy, and the future of work. As AI systems become more capable, 
        we need to ensure that they are developed and deployed responsibly, with proper safeguards and oversight.
        
        Looking ahead, we can expect to see even more exciting developments in the AI space. Researchers are working on next-generation models that promise 
        even greater capabilities, while also addressing current limitations around reasoning, factuality, and safety.
        
        That's all for this week's AI Weekly. Thank you for listening, and we'll see you next time with more insights from the world of artificial intelligence.
        """
        
        metadata_request = {
            "episode_id": str(uuid4()),
            "script": test_script,
            "group_id": str(uuid4()),
            "style_preferences": {
                "tone": "professional",
                "style": "informative"
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8003/generate-metadata",
                json=metadata_request,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Writer service generated metadata successfully")
                logger.info(f"📝 Generated title: {result.get('metadata', {}).get('title', 'N/A')}")
                logger.info(f"📄 Generated description: {result.get('metadata', {}).get('description', 'N/A')[:100]}...")
                return result
            else:
                logger.error(f"❌ Writer service failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Writer service request failed: {e}")
            return False
    
    def test_presenter_service(self):
        """Test the presenter service directly."""
        logger.info("🎤 Testing Presenter Service...")
        
        # Test health
        try:
            response = self.session.get("http://localhost:8004/health")
            if response.status_code == 200:
                logger.info("✅ Presenter service is healthy")
            else:
                logger.error(f"❌ Presenter service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to presenter service: {e}")
            return False
        
        # Test audio generation
        test_script = """
        Welcome to AI Weekly, your source for the latest developments in artificial intelligence and machine learning. 
        I'm Alex Chen, and today we're diving deep into the fascinating world of large language models and their impact on various industries.
        
        In recent news, we've seen remarkable advances in AI technology that are reshaping how we think about human-computer interaction. 
        From GPT models that can engage in natural conversations to specialized AI systems that can write code, create art, and even assist in scientific research, 
        the pace of innovation continues to accelerate.
        
        One of the most exciting developments this week has been the release of new multimodal AI systems that can process both text and images simultaneously. 
        These systems represent a significant leap forward in AI capabilities, enabling more sophisticated understanding of complex, real-world scenarios.
        
        The implications for businesses are profound. Companies across industries are now exploring how to integrate these advanced AI systems into their workflows. 
        From customer service automation to content creation, from data analysis to creative design, AI is becoming an indispensable tool for modern enterprises.
        
        However, with these advances come important considerations about ethics, privacy, and the future of work. As AI systems become more capable, 
        we need to ensure that they are developed and deployed responsibly, with proper safeguards and oversight.
        
        Looking ahead, we can expect to see even more exciting developments in the AI space. Researchers are working on next-generation models that promise 
        even greater capabilities, while also addressing current limitations around reasoning, factuality, and safety.
        
        That's all for this week's AI Weekly. Thank you for listening, and we'll see you next time with more insights from the world of artificial intelligence.
        """
        
        audio_request = {
            "episode_id": str(uuid4()),
            "script": test_script,
            "presenter_ids": [str(uuid4())],
            "voice_settings": {
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8004/generate-audio",
                json=audio_request,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Presenter service generated audio successfully")
                logger.info(f"🎵 Audio URL: {result.get('audio_url', 'N/A')}")
                logger.info(f"⏱️ Duration: {result.get('duration_seconds', 0)} seconds")
                logger.info(f"📁 File size: {result.get('file_size_bytes', 0)} bytes")
                logger.info(f"🎧 Format: {result.get('format', 'N/A')}")
                return result
            else:
                logger.error(f"❌ Presenter service failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Presenter service request failed: {e}")
            return False
    
    def test_text_generation_service(self):
        """Test the text generation service directly."""
        logger.info("📝 Testing Text Generation Service...")
        
        # Test health
        try:
            response = self.session.get("http://localhost:8002/health")
            if response.status_code == 200:
                logger.info("✅ Text Generation service is healthy")
            else:
                logger.error(f"❌ Text Generation service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to text generation service: {e}")
            return False
        
        # Test script generation
        test_articles = [
            {
                "id": str(uuid4()),
                "title": "New AI Model Breaks Performance Records",
                "summary": "A new artificial intelligence model has achieved unprecedented performance on various benchmarks, showing significant improvements in reasoning and language understanding.",
                "content": "Researchers have developed a new AI model that demonstrates remarkable capabilities across multiple domains. The model shows particular strength in complex reasoning tasks and natural language understanding.",
                "publish_date": "2024-01-15T10:00:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI Ethics Guidelines Updated",
                "summary": "Leading AI organizations have released updated guidelines for ethical AI development, emphasizing transparency and accountability.",
                "content": "The new guidelines focus on ensuring AI systems are developed with proper consideration for ethical implications, including bias mitigation and transparency in decision-making processes.",
                "publish_date": "2024-01-14T15:30:00Z"
            }
        ]
        
        script_request = {
            "group_id": str(uuid4()),
            "article_summaries": test_articles,
            "target_duration_minutes": 75,
            "style_preferences": {
                "tone": "professional",
                "style": "informative",
                "target_audience": "tech professionals"
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8002/generate-script",
                json=script_request,
                timeout=300  # 5 minutes for script generation
            )
            
            if response.status_code == 200:
                result = response.json()
                script = result.get('script', '')
                logger.info("✅ Text Generation service generated script successfully")
                logger.info(f"📝 Script length: {len(script)} characters")
                logger.info(f"📊 Estimated duration: {result.get('estimated_duration_minutes', 0)} minutes")
                logger.info(f"📰 Articles used: {len(result.get('articles_used', []))}")
                
                # Check if script is over 1000 words
                word_count = len(script.split())
                if word_count >= 1000:
                    logger.info(f"✅ Script meets requirement: {word_count} words (≥1000)")
                else:
                    logger.warning(f"⚠️ Script is short: {word_count} words (<1000)")
                
                return result
            else:
                logger.error(f"❌ Text Generation service failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Text Generation service request failed: {e}")
            return False


def main():
    """Run all service tests."""
    tester = SimpleServiceTester()
    
    logger.info("🎯 Starting simplified service tests...")
    
    # Test Text Generation Service
    script_result = tester.test_text_generation_service()
    
    if script_result:
        # Test Writer Service
        metadata_result = tester.test_writer_service()
        
        if metadata_result:
            # Test Presenter Service
            audio_result = tester.test_presenter_service()
            
            if audio_result:
                logger.info("🎉 All services tested successfully!")
                logger.info("📋 Test Summary:")
                logger.info(f"  - Script generated: {len(script_result.get('script', ''))} characters")
                logger.info(f"  - Metadata created: {metadata_result.get('metadata', {}).get('title', 'N/A')}")
                logger.info(f"  - Audio generated: {audio_result.get('duration_seconds', 0)} seconds")
            else:
                logger.error("❌ Presenter service test failed")
        else:
            logger.error("❌ Writer service test failed")
    else:
        logger.error("❌ Text Generation service test failed")


if __name__ == "__main__":
    main()
