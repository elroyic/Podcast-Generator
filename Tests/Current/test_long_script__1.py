#!/usr/bin/env python3
"""
Test script that generates a longer script (1000+ words) using Qwen2.5.
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

class LongScriptTester:
    """Test that generates a longer script with Qwen2.5."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:8000"
    
    def create_presenter(self) -> str:
        """Create a presenter and return its ID."""
        logger.info("👤 Creating presenter...")
        
        presenter_data = {
            "name": "Alex Chen",
            "bio": "Tech enthusiast and AI researcher with 10+ years experience in machine learning and software development.",
            "gender": "neutral",
            "country": "US",
            "city": "New York",
            "specialties": ["technology", "podcasting"],
            "expertise": ["AI", "software development"],
            "interests": ["tech news", "innovation"]
        }
        
        response = self.session.post(f"{self.base_url}/api/presenters", json=presenter_data)
        if response.status_code == 200:
            presenter = response.json()
            logger.info(f"✅ Created presenter: {presenter['name']} (ID: {presenter['id']})")
            return presenter['id']
        else:
            raise Exception(f"Failed to create presenter: {response.status_code} - {response.text}")
    
    def create_writer(self) -> str:
        """Create a writer and return its ID."""
        logger.info("✍️ Creating writer...")
        
        writer_data = {
            "name": "AI Script Writer",
            "capabilities": ["title", "description", "tags", "keywords", "category", "subcategory"]
        }
        
        response = self.session.post(f"{self.base_url}/api/writers", json=writer_data)
        if response.status_code == 200:
            writer = response.json()
            logger.info(f"✅ Created writer: {writer['name']} (ID: {writer['id']})")
            return writer['id']
        else:
            raise Exception(f"Failed to create writer: {response.status_code} - {response.text}")
    
    def create_news_feed(self) -> str:
        """Create a news feed and return its ID."""
        logger.info("📰 Creating news feed...")
        
        feed_data = {
            "name": "TechCrunch RSS",
            "source_url": "https://techcrunch.com/feed/",
            "type": "RSS",
            "is_active": True
        }
        
        response = self.session.post(f"{self.base_url}/api/news-feeds", json=feed_data)
        if response.status_code == 200:
            feed = response.json()
            logger.info(f"✅ Created news feed: {feed['name']} (ID: {feed['id']})")
            return feed['id']
        else:
            raise Exception(f"Failed to create news feed: {response.status_code} - {response.text}")
    
    def create_podcast_group(self, presenter_id: str, writer_id: str, news_feed_id: str) -> str:
        """Create a podcast group and return its ID."""
        logger.info("🎙️ Creating podcast group...")
        
        group_data = {
            "name": "AI Weekly",
            "description": "Weekly podcast covering the latest developments in artificial intelligence and machine learning.",
            "category": "Technology",
            "subcategory": "AI News",
            "language": "en",
            "country": "US",
            "tags": ["AI", "technology", "news"],
            "keywords": ["artificial intelligence", "machine learning", "tech news"],
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "status": "active",
            "presenter_ids": [presenter_id],
            "writer_id": writer_id,
            "news_feed_ids": [news_feed_id]
        }
        
        response = self.session.post(f"{self.base_url}/api/podcast-groups", json=group_data)
        if response.status_code == 200:
            group = response.json()
            logger.info(f"✅ Created podcast group: {group['name']} (ID: {group['id']})")
            return group['id']
        else:
            raise Exception(f"Failed to create podcast group: {response.status_code} - {response.text}")
    
    def generate_long_script(self, group_id: str) -> Dict[str, Any]:
        """Generate a longer script using Qwen2.5 with more articles and longer duration."""
        logger.info("📝 Generating long script with Qwen2.5...")
        
        # Comprehensive test articles for longer script
        test_articles = [
            {
                "id": str(uuid4()),
                "title": "Revolutionary AI Model Achieves Human-Level Performance",
                "summary": "A groundbreaking artificial intelligence model has achieved unprecedented performance across multiple benchmarks, demonstrating capabilities that rival human experts in complex reasoning, creative writing, and technical problem-solving. The model represents a significant leap forward in AI development.",
                "content": "Researchers have developed a new AI model that demonstrates remarkable capabilities across multiple domains. The model shows particular strength in complex reasoning tasks, natural language understanding, and creative problem-solving. This breakthrough represents a significant advancement in the field of artificial intelligence, with potential applications spanning from scientific research to business automation. The model's architecture incorporates several novel techniques that enable it to process information more efficiently and accurately than previous generations of AI systems. The implications for various industries are profound, as this technology could revolutionize how we approach complex challenges in healthcare, education, finance, and beyond. The model's training process involved massive datasets and sophisticated algorithms that allow it to understand context, nuance, and subtle patterns in human communication. This represents a major milestone in the quest to create truly intelligent machines that can assist humans in complex tasks.",
                "publish_date": "2024-01-15T10:00:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI Ethics Framework Updated for Responsible Development",
                "summary": "Leading AI organizations have released comprehensive updated guidelines for ethical AI development, emphasizing transparency, accountability, and fairness. The new framework addresses critical concerns about bias, privacy, and the societal impact of AI technologies.",
                "content": "The new guidelines focus on ensuring AI systems are developed with proper consideration for ethical implications, including bias mitigation and transparency in decision-making processes. These guidelines represent a collaborative effort between industry leaders, academic researchers, and policy makers to establish best practices for responsible AI development. The framework addresses key concerns such as algorithmic bias, data privacy, and the societal impact of AI technologies. It provides detailed recommendations for developers, researchers, and organizations working with AI systems, covering everything from data collection and model training to deployment and monitoring. The guidelines emphasize the importance of human oversight and the need for AI systems to be explainable and auditable. They also address concerns about job displacement and the need for retraining programs to help workers adapt to an AI-driven economy.",
                "publish_date": "2024-01-14T15:30:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Machine Learning Transforms Healthcare Diagnosis",
                "summary": "New applications of machine learning in healthcare are showing remarkable results in early disease detection, treatment optimization, and personalized medicine. Healthcare providers are increasingly adopting AI-powered tools for diagnostic assistance and patient care.",
                "content": "Healthcare providers are increasingly adopting AI-powered tools for diagnostic assistance, treatment planning, and patient monitoring. These systems are helping to improve outcomes while reducing costs. The integration of machine learning in healthcare represents a paradigm shift in how medical professionals approach diagnosis and treatment. From radiology to drug discovery, AI is transforming every aspect of healthcare delivery. Recent studies have shown that AI systems can detect certain conditions earlier and more accurately than traditional methods, potentially saving lives and reducing healthcare costs. The technology is particularly effective in image analysis, where AI can identify patterns that might be missed by human eyes. This has led to significant improvements in cancer detection, stroke diagnosis, and other critical medical applications.",
                "publish_date": "2024-01-13T08:45:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Quantum Computing Accelerates AI Research",
                "summary": "The intersection of quantum computing and artificial intelligence is opening new possibilities for solving complex problems that are intractable for classical computers. Researchers are exploring how quantum algorithms can accelerate AI training and inference processes.",
                "content": "Quantum computing represents a revolutionary approach to computation that leverages the principles of quantum mechanics. When combined with artificial intelligence, it opens up new possibilities for solving complex optimization problems, simulating quantum systems, and advancing machine learning algorithms. Researchers are exploring how quantum algorithms can accelerate AI training and inference processes. This emerging field promises to tackle problems that are currently impossible for classical computers to solve efficiently, potentially leading to breakthroughs in cryptography, materials science, and complex system optimization. The combination of quantum computing and AI could lead to new discoveries in drug development, financial modeling, and climate science.",
                "publish_date": "2024-01-12T14:20:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI Solutions for Climate Change Challenges",
                "summary": "Artificial intelligence is being leveraged to address climate change through improved weather prediction, energy optimization, and environmental monitoring systems. These applications demonstrate how technology can be harnessed for environmental protection.",
                "content": "Climate change represents one of the most pressing challenges of our time, and artificial intelligence is emerging as a powerful tool in the fight against environmental degradation. AI systems are being used to improve weather prediction models, optimize energy consumption, and monitor environmental changes. These applications demonstrate how technology can be harnessed for the greater good of humanity and the planet. From smart grids that optimize energy distribution to satellite systems that monitor deforestation, AI is playing a crucial role in environmental protection and climate change mitigation. The technology is also being used to develop more efficient renewable energy systems and to optimize transportation networks to reduce carbon emissions.",
                "publish_date": "2024-01-11T09:15:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Autonomous Vehicles Reach New Milestones",
                "summary": "Self-driving car technology has reached new levels of sophistication, with advanced AI systems enabling safer and more efficient autonomous navigation. The latest developments bring us closer to widespread adoption of autonomous vehicles.",
                "content": "The autonomous vehicle industry has reached significant milestones in recent months, with AI-powered systems demonstrating improved safety and reliability. These advances are bringing us closer to a future where self-driving cars are commonplace on our roads. The technology combines computer vision, sensor fusion, and machine learning to create vehicles that can navigate complex traffic situations with minimal human intervention. Safety remains the top priority, with extensive testing and validation ensuring that these systems meet the highest standards before deployment. The latest developments include improved object recognition, better decision-making algorithms, and enhanced communication between vehicles and infrastructure.",
                "publish_date": "2024-01-10T16:30:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI-Powered Education Personalizes Learning",
                "summary": "Educational technology powered by artificial intelligence is revolutionizing how students learn, providing personalized instruction and adaptive learning experiences that cater to individual needs and learning styles.",
                "content": "AI-powered educational tools are transforming the learning experience by providing personalized instruction and adaptive learning paths. These systems can identify individual student strengths and weaknesses, adjusting the curriculum accordingly. The technology enables educators to provide more effective instruction while giving students the support they need to succeed. From intelligent tutoring systems to automated grading and feedback, AI is making education more accessible and effective for learners of all ages and backgrounds. The systems can adapt to different learning styles and provide real-time feedback to help students improve their understanding of complex concepts.",
                "publish_date": "2024-01-09T11:45:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Natural Language Processing Advances Communication",
                "summary": "Recent breakthroughs in natural language processing are enabling more natural and intuitive interactions between humans and machines, with applications ranging from customer service to creative writing assistance.",
                "content": "Natural language processing has made significant strides in recent years, enabling machines to understand and generate human language with unprecedented accuracy. These advances are making it possible for people to interact with technology in more natural and intuitive ways. From chatbots that can handle complex customer service inquiries to AI writing assistants that help with creative projects, NLP is transforming how we communicate with machines. The technology is also being used to break down language barriers, enabling real-time translation and cross-cultural communication. These developments have implications for everything from business communication to international diplomacy.",
                "publish_date": "2024-01-08T13:20:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Computer Vision Revolutionizes Industry",
                "summary": "Advanced computer vision systems are being deployed across various industries, from manufacturing quality control to retail analytics, demonstrating the transformative potential of AI-powered visual recognition.",
                "content": "Computer vision technology has reached new levels of sophistication, enabling machines to interpret and understand visual information with remarkable accuracy. These systems are being deployed across a wide range of industries, from manufacturing and agriculture to healthcare and retail. In manufacturing, computer vision is being used for quality control, defect detection, and process optimization. In agriculture, it's helping farmers monitor crop health and optimize irrigation. In healthcare, it's assisting with medical imaging and surgical procedures. The technology is also being used in retail for inventory management, customer behavior analysis, and loss prevention.",
                "publish_date": "2024-01-07T10:15:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI in Financial Services Transforms Banking",
                "summary": "Financial institutions are increasingly adopting AI technologies for fraud detection, risk assessment, and customer service, leading to more secure and efficient banking operations.",
                "content": "The financial services industry is undergoing a transformation driven by artificial intelligence, with banks and other institutions adopting AI technologies to improve security, efficiency, and customer experience. AI systems are being used for fraud detection, risk assessment, and automated trading. These technologies can analyze vast amounts of financial data to identify suspicious patterns and potential risks. They're also being used to provide personalized financial advice and to automate routine banking operations. The result is a more secure, efficient, and customer-friendly banking experience that leverages the power of AI to provide better services while reducing costs.",
                "publish_date": "2024-01-06T14:30:00Z"
            }
        ]
        
        script_request = {
            "group_id": group_id,
            "article_summaries": test_articles,
            "target_duration_minutes": 300,  # 5 hours to ensure 1000+ words
            "style_preferences": {
                "tone": "professional",
                "style": "informative",
                "target_audience": "tech professionals",
                "detailed_analysis": True,
                "include_examples": True,
                "comprehensive_coverage": True,
                "in_depth_discussion": True,
                "extensive_coverage": True,
                "detailed_explanations": True,
                "comprehensive_analysis": True
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8002/generate-script",
                json=script_request,
                timeout=1200  # 20 minutes for longer script generation
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
                return None
                
        except Exception as e:
            logger.error(f"❌ Text Generation service request failed: {e}")
            return None
    
    def test_writer_service(self, script: str, group_id: str) -> Dict[str, Any]:
        """Test writer service for metadata generation."""
        logger.info("✍️ Testing Writer Service...")
        
        metadata_request = {
            "episode_id": str(uuid4()),
            "script": script,
            "group_id": group_id,
            "style_preferences": {
                "tone": "professional",
                "style": "informative"
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8003/generate-metadata",
                json=metadata_request,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Writer service generated metadata successfully")
                logger.info(f"📝 Generated title: {result.get('metadata', {}).get('title', 'N/A')}")
                logger.info(f"📄 Generated description: {result.get('metadata', {}).get('description', 'N/A')[:100]}...")
                return result
            else:
                logger.error(f"❌ Writer service failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Writer service request failed: {e}")
            return None
    
    def test_presenter_service(self, script: str) -> Dict[str, Any]:
        """Test presenter service for audio generation."""
        logger.info("🎤 Testing Presenter Service...")
        
        audio_request = {
            "episode_id": str(uuid4()),
            "script": script,
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
                timeout=600  # 10 minutes for audio generation
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
                return None
                
        except Exception as e:
            logger.error(f"❌ Presenter service request failed: {e}")
            return None


def main():
    """Run the long script generation test with Qwen2.5."""
    tester = LongScriptTester()
    
    logger.info("🎯 Starting long script generation test with Qwen2.5...")
    
    try:
        # Step 1: Set up database entities
        presenter_id = tester.create_presenter()
        writer_id = tester.create_writer()
        news_feed_id = tester.create_news_feed()
        group_id = tester.create_podcast_group(presenter_id, writer_id, news_feed_id)
        
        # Step 2: Generate long script with Qwen2.5
        script_result = tester.generate_long_script(group_id)
        
        if script_result:
            script = script_result.get('script', '')
            
            # Step 3: Test Writer Service
            metadata_result = tester.test_writer_service(script, group_id)
            
            if metadata_result:
                # Step 4: Test Presenter Service
                audio_result = tester.test_presenter_service(script)
                
                if audio_result:
                    logger.info("🎉 All services tested successfully!")
                    logger.info("📋 Final Test Summary:")
                    logger.info(f"  - Script generated: {len(script)} characters")
                    logger.info(f"  - Word count: {len(script.split())} words")
                    logger.info(f"  - Metadata created: {metadata_result.get('metadata', {}).get('title', 'N/A')}")
                    logger.info(f"  - Audio generated: {audio_result.get('duration_seconds', 0)} seconds")
                    logger.info(f"  - Audio format: {audio_result.get('format', 'N/A')}")
                    logger.info(f"  - File size: {audio_result.get('file_size_bytes', 0)} bytes")
                    
                    # Check requirements
                    word_count = len(script.split())
                    if word_count >= 1000:
                        logger.info("✅ Script meets 1000+ word requirement")
                    else:
                        logger.warning(f"⚠️ Script is {word_count} words, less than required 1000")
                    
                    if audio_result.get('format', '').lower() == 'mp3':
                        logger.info("✅ Audio is in MP3 format as requested")
                    else:
                        logger.warning(f"⚠️ Audio format is {audio_result.get('format', 'unknown')}, not MP3")
                    
                    # Show first few lines of script
                    script_lines = script.split('\n')[:10]
                    logger.info("📝 Script preview:")
                    for line in script_lines:
                        if line.strip():
                            logger.info(f"  {line.strip()}")
                    
                else:
                    logger.error("❌ Presenter service test failed")
            else:
                logger.error("❌ Writer service test failed")
        else:
            logger.error("❌ Text Generation service test failed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
