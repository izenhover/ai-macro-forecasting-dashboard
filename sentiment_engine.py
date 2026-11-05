"""موتور تحلیل احساسات اخبار"""

import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from loguru import logger
from config import CONFIG


class SentimentEngine:
    """تحلیل Sentiment با FinBERT و مدل‌های زبانی"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """بارگذاری مدل FinBERT"""
        try:
            logger.info("🧠 بارگذاری مدل Sentiment...")
            model_name = CONFIG.sentiment.model_name
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name
            )
            self.model.eval()
            logger.info("✅ مدل Sentiment بارگذاری شد")
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری مدل: {e}")
            self.model = None
    
    def analyze(self, text: str, source: str = "default") -> dict:
        """تحلیل احساسات یک متن"""
        if self.model is None:
            return self._fallback_analysis(text)
        
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            probs = probs.numpy()[0]
            
            # FinBERT: [negative, neutral, positive]
            sentiment_score = float(probs[2] - probs[0])  # positive - negative
            
            # تنظیم بر اساس اعتبار منبع
            credibility = CONFIG.sentiment.source_credibility.get(
                source, 
                CONFIG.sentiment.source_credibility["default"]
            )
            adjusted_score = sentiment_score * credibility
            
            return {
                "sentiment_score": adjusted_score,
                "raw_score": sentiment_score,
                "confidence": float(max(probs)),
                "credibility": credibility,
                "negative_prob": float(probs[0]),
                "neutral_prob": float(probs[1]),
                "positive_prob": float(probs[2]),
            }
        except Exception as e:
            logger.error(f"❌ خطا در تحلیل Sentiment: {e}")
            return self._fallback_analysis(text)
    
    def _fallback_analysis(self, text: str) -> dict:
        """تحلیل ساده در صورت عدم دسترسی به مدل"""
        # کلمات کلیدی فارسی
        positive_words = [
            "رشد", "افزایش", "بهبود", "توافق", "صلح", "سرمایه‌گذاری",
            "توسعه", "رونق", "کاهش تورم"
        ]
        negative_words = [
            "تحریم", "افت", "کاهش", "بحران", "تنش", "جنگ", "تورم",
            "رکود", "افزایش قیمت", "کمبود"
        ]
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / total
        
        return {
            "sentiment_score": score * 0.5,  # وزن پایین‌تر
            "raw_score": score,
            "confidence": 0.5,
            "credibility": 0.5,
            "negative_prob": 0.33,
            "neutral_prob": 0.34,
            "positive_prob": 0.33,
        }
    
    def batch_analyze(self, texts: list, sources: list = None) -> list:
        """تحلیل دسته‌ای"""
        if sources is None:
            sources = ["default"] * len(texts)
        
        results = []
        for text, source in zip(texts, sources):
            results.append(self.analyze(text, source))
        return results
    
    def aggregate_sentiment(self, results: list, window: int = 5) -> dict:
        """تجمیع Sentiment"""
        if not results:
            return {"avg_sentiment": 0.0, "sentiment_momentum": 0.0}
        
        scores = [r["sentiment_score"] for r in results]
        confidences = [r["confidence"] for r in results]
        
        weighted_scores = np.array(scores) * np.array(confidences)
        avg_sentiment = float(np.mean(weighted_scores))
        
        # مومنتوم
        if len(scores) > window:
            recent = np.mean(scores[-window:])
            older = np.mean(scores[-2*window:-window])
            momentum = recent - older
        else:
            momentum = 0.0
        
        return {
            "avg_sentiment": avg_sentiment,
            "sentiment_momentum": float(momentum),
            "count": len(results),
        }