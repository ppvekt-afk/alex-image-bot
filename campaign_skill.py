import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class ImageCampaign:
    def __init__(self):
        self.campaigns_dir = Path("generated_campaigns")
        self.campaigns_dir.mkdir(exist_ok=True)
    
    def create_brief(self, product: str, audience: str, aspect_ratio: str = "1:1", count: int = 3) -> Dict:
        return {
            "product": product,
            "audience": audience,
            "aspect_ratio": aspect_ratio,
            "count": min(count, 5),
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_prompts(self, brief: Dict) -> List[Dict]:
        product = brief["product"]
        audience = brief["audience"]
        ratio = brief["aspect_ratio"]
        
        prompts = [
            {
                "name": f"Hero - {product}",
                "prompt": f"Professional product photography of {product}, targeting {audience}, cinematic lighting, premium quality, {ratio}",
                "style": "premium"
            },
            {
                "name": f"Lifestyle - {product}", 
                "prompt": f"Lifestyle shot of people using {product}, {audience} demographic, natural lighting, authentic moment, {ratio}",
                "style": "lifestyle"
            },
            {
                "name": f"Abstract - {product}",
                "prompt": f"Abstract artistic representation of {product}, modern design, bold colors, {audience} appeal, {ratio}",
                "style": "abstract"
            },
            {
                "name": f"Minimalist - {product}",
                "prompt": f"Minimalist composition featuring {product}, clean background, professional lighting, {ratio}",
                "style": "minimalist"
            },
            {
                "name": f"Bold - {product}",
                "prompt": f"Dramatic high-contrast image of {product}, attention-grabbing, for {audience}, {ratio}",
                "style": "bold"
            }
        ]
        return prompts[:brief["count"]]
    
    def save_campaign(self, brief: Dict, prompts: List[Dict]) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        campaign_file = self.campaigns_dir / f"campaign_{timestamp}.json"
        
        data = {
            "brief": brief,
            "concepts": prompts,
            "status": "prompts_ready"
        }
        
        with open(campaign_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return campaign_file
    
    def format_output(self, brief: Dict, prompts: List[Dict]) -> str:
        output = f"📊 *Image Campaign Brief*\n\n"
        output += f"📦 Product: {brief['product']}\n"
        output += f"👥 Audience: {brief['audience']}\n"
        output += f"📐 Aspect Ratio: {brief['aspect_ratio']}\n"
        output += f"🔢 Concepts: {brief['count']}\n\n"
        output += "*🎨 Generated Prompts:*\n\n"
        
        for i, p in enumerate(prompts, 1):
            output += f"{i}. *{p['name']}* ({p['style']})\n"
            output += f"   `{p['prompt'][:100]}...`\n\n"
        
        output += "✨ *Next Steps:*\n"
        output += "• Send /generate_campaign to create images\n"
        output += "• Or use prompts manually with /image"
        
        return output
