import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class AmazonListingGenerator:
    def __init__(self):
        self.output_dir = Path("generated_amazon_listings")
        self.output_dir.mkdir(exist_ok=True)
    
    def create_listing(self, product_name: str, product_category: str, key_features: str, target_buyer: str = "general consumer") -> Dict:
        features_list = [f.strip() for f in key_features.split(",")]
        return {
            "product_name": product_name,
            "product_category": product_category,
            "key_features": features_list,
            "target_buyer": target_buyer,
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_hero_prompt(self, product_name: str) -> str:
        return f"Professional Amazon main listing hero image of {product_name}. Pure white background, product centered, perfectly lit with soft studio lighting, no shadows, commercial product photography, 2000x2000px quality"
    
    def generate_lifestyle_prompt(self, product_name: str, product_category: str, target_buyer: str) -> str:
        return f"Amazon lifestyle image of {product_name} being used by {target_buyer} in natural setting. {product_category} product in real-life use context, warm lighting, aspirational, commercial lifestyle photography"
    
    def generate_infographic_prompt(self, product_name: str, key_features: List[str]) -> str:
        features_text = ", ".join(key_features[:5])
        return f"Amazon product infographic for {product_name}. Shows product with callout arrows highlighting: {features_text}. Clean white background, professional typography, Amazon A+ content style"
    
    def generate_detail_prompt(self, product_name: str) -> str:
        return f"Extreme closeup macro product detail shot of {product_name}, focus on premium materials and texture, studio lighting, white background, ultra sharp focus, Amazon product detail image"
    
    def save_listing(self, listing: Dict, prompts: Dict) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        listing_file = self.output_dir / f"amazon_listing_{listing['product_name'].replace(' ', '_')}_{timestamp}.json"
        
        data = {
            "brief": listing,
            "prompts": prompts,
            "status": "prompts_ready"
        }
        
        with open(listing_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return listing_file
    
    def format_output(self, listing: Dict, prompts: Dict) -> str:
        output = f"📦 AMAZON PRODUCT LISTING\n\n"
        output += f"Продукт: {listing['product_name']}\n"
        output += f"Категория: {listing['product_category']}\n"
        output += f"Аудитория: {listing['target_buyer']}\n"
        output += f"Ключевые особенности:\n"
        for f in listing['key_features'][:5]:
            output += f"  • {f}\n"
        output += f"\n📷 БУДУТ СОЗДАНЫ 4 ИЗОБРАЖЕНИЯ:\n"
        output += f"1. Hero image (белый фон)\n"
        output += f"2. Lifestyle shot\n"
        output += f"3. Feature infographic\n"
        output += f"4. Closeup detail\n\n"
        output += f"Отправьте /generate_amazon_listing для создания изображений"
        
        return output
