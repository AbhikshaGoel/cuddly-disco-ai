"""
AI Engine: 3-Layer Intelligent Processing
Layer 1: Cloudflare Workers AI (Fast, Batch Processing)
Layer 2: Local SentenceTransformer (Reliable Fallback)
Layer 3: Regex Pattern Matching (Ultimate Fallback)
"""
import os
import re
import time
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from config import (
    CATEGORY_ANCHORS,
    REGEX_FALLBACK,
    CLOUDFLARE_CONFIG,
    LOCAL_AI_CONFIG
)

logger = logging.getLogger(__name__)


class CloudflareEmbedding:
    """Handles Cloudflare Workers AI API with batch processing"""
    
    def __init__(self):
        self.account_id = CLOUDFLARE_CONFIG["account_id"]
        self.api_token = CLOUDFLARE_CONFIG["api_token"]
        self.model = CLOUDFLARE_CONFIG["model"]
        self.batch_size = CLOUDFLARE_CONFIG["batch_size"]
        self.max_retries = CLOUDFLARE_CONFIG["max_retries"]
        self.retry_delay = CLOUDFLARE_CONFIG["retry_delay"]
        self.timeout = CLOUDFLARE_CONFIG["timeout"]
        
        # Build API URL
        self.url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )
        
        # Validate configuration
        self.is_configured = bool(self.account_id and self.api_token)
        
        if self.is_configured:
            logger.info(f"✅ Cloudflare AI initialized: {self.model}")
        else:
            logger.warning("⚠️ Cloudflare credentials missing")
    
    def _make_request(self, texts: List[str], attempt: int = 1) -> Optional[List[List[float]]]:
        """Make API request with retry logic"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Cloudflare expects {"text": ["sentence1", "sentence2"]}
            payload = {
                "text": texts,
                "pooling": CLOUDFLARE_CONFIG["pooling"]  # Use 'cls' for better accuracy
            }
            
            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Cloudflare response: {"result": {"data": [[...], [...]]}}
                if "result" in data and "data" in data["result"]:
                    embeddings = data["result"]["data"]
                    logger.debug(f"✅ Cloudflare: Generated {len(embeddings)} embeddings")
                    return embeddings
                else:
                    logger.error(f"Unexpected Cloudflare response format: {data}")
                    return None
            
            elif response.status_code == 429:
                # Rate limited
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⏳ Rate limited. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    return self._make_request(texts, attempt + 1)
                else:
                    logger.error("❌ Rate limit exceeded, max retries reached")
                    return None
            
            else:
                logger.error(f"Cloudflare API error {response.status_code}: {response.text}")
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Request timeout after {self.timeout}s")
            return None
        
        except Exception as e:
            logger.error(f"❌ Cloudflare request failed: {e}")
            return None
    
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings with automatic batching"""
        if not self.is_configured or not texts:
            return None
        
        # Process in batches
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"🔄 Processing {len(texts)} texts in {total_batches} batches...")
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            logger.debug(f"Batch {batch_num}/{total_batches}: {len(batch)} items")
            
            embeddings = self._make_request(batch)
            
            if embeddings is None:
                logger.error(f"❌ Batch {batch_num} failed")
                return None  # Fail entire request if any batch fails
            
            all_embeddings.extend(embeddings)
            
            # Rate limiting protection (50 batches = ~2500 items @ batch_size=50)
            # At 3000 req/min, sleep briefly between batches
            if batch_num < total_batches:
                time.sleep(0.1)  # 100ms between batches
        
        logger.info(f"✅ Cloudflare: Generated {len(all_embeddings)} total embeddings")
        return all_embeddings


class LocalEmbedding:
    """Fallback to local SentenceTransformer models"""
    
    def __init__(self):
        self.model = None
        self.model_name = None
        self.is_available = False
        
        # Try importing
        try:
            from sentence_transformers import SentenceTransformer
            self.SentenceTransformer = SentenceTransformer
            self.is_available = True
            logger.info("✅ SentenceTransformers library available")
        except ImportError:
            logger.warning("⚠️ SentenceTransformers not installed (pip install sentence-transformers)")
    
    def _load_model(self, model_name: str):
        """Lazy load model only when needed"""
        if self.model is None or self.model_name != model_name:
            logger.info(f"📥 Loading local model: {model_name}...")
            self.model = self.SentenceTransformer(model_name)
            self.model_name = model_name
    
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings using local model"""
        if not self.is_available or not texts:
            return None
        
        try:
            # Try primary model first
            self._load_model(LOCAL_AI_CONFIG["primary_model"])
            
            logger.info(f"🧠 Local AI processing {len(texts)} texts...")
            
            embeddings = self.model.encode(
                texts,
                batch_size=LOCAL_AI_CONFIG["batch_size"],
                show_progress_bar=LOCAL_AI_CONFIG["show_progress_bar"],
                convert_to_numpy=True
            )
            
            # Convert to list format
            result = embeddings.tolist()
            logger.info(f"✅ Local AI: Generated {len(result)} embeddings")
            return result
        
        except Exception as e:
            logger.error(f"❌ Local AI failed: {e}")
            return None


class RegexClassifier:
    """Last resort: Pure regex-based classification"""
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile regex patterns for performance"""
        compiled = {}
        for category, patterns in REGEX_FALLBACK.items():
            compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classify text using regex patterns
        Returns: (category, confidence_score)
        """
        text_lower = text.lower()
        
        # Score each category
        scores = {}
        for category, patterns in self.patterns.items():
            match_count = sum(1 for pattern in patterns if pattern.search(text_lower))
            scores[category] = match_count
        
        # Find best match
        if scores:
            best_category = max(scores, key=scores.get)
            max_score = scores[best_category]
            
            if max_score > 0:
                # Confidence based on number of matches
                confidence = min(max_score / 3.0, 1.0)  # Max out at 3 matches
                return best_category, confidence
        
        return "GENERAL", 0.3  # Default with low confidence


class AIEngine:
    """
    Main AI Engine: Coordinates all 3 layers
    """
    
    def __init__(self):
        # Initialize all layers
        self.cloudflare = CloudflareEmbedding()
        self.local = LocalEmbedding()
        self.regex = RegexClassifier()
        
        # Pre-compute category anchor embeddings
        self.anchor_embeddings = None
        self.anchor_method = None
        self._initialize_anchors()
    
    def _initialize_anchors(self):
        """Generate embeddings for category descriptions once at startup"""
        descriptions = [data["desc"] for data in CATEGORY_ANCHORS.values()]
        categories = list(CATEGORY_ANCHORS.keys())
        
        logger.info("🧠 Pre-computing Category Anchor embeddings...")
        
        # Try Cloudflare first
        embeddings = self.cloudflare.generate_embeddings(descriptions)
        if embeddings:
            self.anchor_embeddings = dict(zip(categories, embeddings))
            self.anchor_method = "cloudflare"
            logger.info(f"✅ Anchors computed via Cloudflare ({len(embeddings)} categories)")
            return
        
        # Fallback to local
        embeddings = self.local.generate_embeddings(descriptions)
        if embeddings:
            self.anchor_embeddings = dict(zip(categories, embeddings))
            self.anchor_method = "local"
            logger.info(f"✅ Anchors computed via Local AI ({len(embeddings)} categories)")
            return
        
        # If both failed, we'll use regex only
        self.anchor_method = "regex"
        logger.warning("⚠️ Using Regex-only mode (no embeddings)")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _categorize_by_embedding(
        self, 
        embedding: List[float], 
        text: str
    ) -> Tuple[str, float, List[float]]:
        """Categorize using vector similarity"""
        best_category = "GENERAL"
        best_similarity = -1.0
        
        for category, anchor_vec in self.anchor_embeddings.items():
            similarity = self._cosine_similarity(embedding, anchor_vec)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_category = category
        
        # Calculate final score
        weight = CATEGORY_ANCHORS.get(best_category, {}).get("weight", 0)
        
        if best_category == "NOISE":
            score = -50.0
        else:
            # Formula: (similarity * 10) + category_weight
            score = (best_similarity * 10.0) + weight
        
        return best_category, round(score, 2), embedding
    
    def _categorize_by_regex(self, text: str) -> Tuple[str, float, None]:
        """Categorize using regex patterns"""
        category, confidence = self.regex.classify(text)
        
        # Get weight for category
        weight = CATEGORY_ANCHORS.get(category, {}).get("weight", 0)
        
        if category == "NOISE":
            score = -50.0
        else:
            # Base score + weight + confidence bonus
            score = 5.0 + weight + (confidence * 5.0)
        
        return category, round(score, 2), None
    
    def process_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Process multiple articles in batch
        Returns articles with added fields: category, score, embedding
        """
        if not articles:
            return []
        
        logger.info(f"🚀 Processing {len(articles)} articles...")
        
        # Prepare texts for embedding
        texts = [f"{art.get('title', '')} {art.get('summary', '')}" for art in articles]
        
        # Try to get embeddings
        embeddings = None
        
        # Layer 1: Cloudflare
        if self.anchor_embeddings and self.anchor_method in ["cloudflare", "local"]:
            logger.info("🔄 Attempting Cloudflare batch embedding...")
            embeddings = self.cloudflare.generate_embeddings(texts)
            
            # Layer 2: Local AI
            if embeddings is None:
                logger.info("🔄 Cloudflare failed, trying Local AI...")
                embeddings = self.local.generate_embeddings(texts)
        
        # Process each article
        processed = []
        for i, article in enumerate(articles):
            text = texts[i]
            
            if embeddings and i < len(embeddings):
                # Use embedding-based classification
                category, score, embedding = self._categorize_by_embedding(
                    embeddings[i], text
                )
                method = "embedding"
            else:
                # Layer 3: Regex fallback
                category, score, embedding = self._categorize_by_regex(text)
                method = "regex"
            
            # Add fields to article
            article["category"] = category
            article["score"] = score
            article["embedding"] = embedding
            article["classification_method"] = method
            
            processed.append(article)
        
        # Log method distribution
        methods = {}
        for art in processed:
            method = art.get("classification_method", "unknown")
            methods[method] = methods.get(method, 0) + 1
        
        logger.info(f"✅ Processed {len(processed)} articles: {methods}")
        
        return processed
    
    def categorize_single(self, article: Dict) -> Dict:
        """Process a single article (useful for testing)"""
        result = self.process_articles([article])
        return result[0] if result else article


# Convenience function for backward compatibility
def categorize_and_score(article: Dict) -> Dict:
    """Legacy function - now delegates to AIEngine"""
    engine = AIEngine()
    return engine.categorize_single(article)