import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class BrandKitGenerator:
    def __init__(self):
        self.output_dir = Path("generated_brand_kits")
        self.output_dir.mkdir(exist_ok=True)
    
    def create_brand_kit(self, brand_name: str, industry: str, personality: str = "modern, trustworthy, approachable", color_preference: str = "") -> Dict:
        return {
            "brand_name": brand_name,
            "industry": industry,
            "personality": personality,
            "color_preference": color_preference,
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_logo_prompts(self, brand_name: str, industry: str, personality: str, color_preference: str) -> Dict:
        prompts = {
            "logo_a": f"Minimalist logo for '{brand_name}', {industry} brand, {personality} personality. Clean vector-style wordmark on white background, professional, flat design. {color_preference}",
            "logo_b": f"Modern logo mark + wordmark for '{brand_name}', {industry}, {personality}. Bold, distinctive, scalable icon design, white background. {color_preference}"
        }
        return prompts
    
    def generate_moodboard_prompt(self, brand_name: str, industry: str, personality: str, color_preference: str) -> str:
        return f"Brand moodboard for a {personality} {industry} brand called '{brand_name}'. Show 5 color palette swatches with hex labels, 4 lifestyle photo tiles, typography samples. Flat lay design, white background. {color_preference}"
    
    def generate_pattern_prompt(self, brand_name: str, industry: str, personality: str, color_preference: str) -> str:
        return f"Seamless brand pattern for {brand_name}, {industry}, {personality} aesthetic. Subtle, tileable, modern. {color_preference}"
    
    def get_color_palette(self, personality: str) -> Dict:
        personality_lower = personality.lower()
        
        if "luxury" in personality_lower or "elegant" in personality_lower:
            return {
                "Primary": "#1A1A1A",
                "Secondary": "#C8A951",
                "Accent": "#FFFFFF",
                "Neutral Light": "#F5F5F5",
                "Neutral Dark": "#333333"
            }
        elif "tech" in personality_lower or "modern" in personality_lower:
            return {
                "Primary": "#0066FF",
                "Secondary": "#00C4FF",
                "Accent": "#7B2CBF",
                "Neutral Light": "#F8F9FA",
                "Neutral Dark": "#212529"
            }
        elif "natural" in personality_lower or "organic" in personality_lower:
            return {
                "Primary": "#2D6A4F",
                "Secondary": "#74C69D",
                "Accent": "#D8F3DC",
                "Neutral Light": "#FEFAE0",
                "Neutral Dark": "#5C4033"
            }
        elif "bold" in personality_lower or "edgy" in personality_lower:
            return {
                "Primary": "#E63946",
                "Secondary": "#F4A261",
                "Accent": "#264653",
                "Neutral Light": "#F1FAEE",
                "Neutral Dark": "#1D3557"
            }
        else:
            return {
                "Primary": "#4A90E2",
                "Secondary": "#50E3C2",
                "Accent": "#F5A623",
                "Neutral Light": "#FFFFFF",
                "Neutral Dark": "#333333"
            }
    
    def get_typography_pairing(self, personality: str) -> Dict:
        personality_lower = personality.lower()
        
        if "luxury" in personality_lower or "elegant" in personality_lower:
            return {
                "heading": "Playfair Display",
                "body": "Cormorant Garamond",
                "url": "https://fonts.google.com/share?selection.family=Playfair+Display|Cormorant+Garamond"
            }
        elif "tech" in personality_lower or "modern" in personality_lower:
            return {
                "heading": "Space Grotesk",
                "body": "Inter",
                "url": "https://fonts.google.com/share?selection.family=Space+Grotesk|Inter"
            }
        elif "natural" in personality_lower or "organic" in personality_lower:
            return {
                "heading": "Quicksand",
                "body": "Lora",
                "url": "https://fonts.google.com/share?selection.family=Quicksand|Lora"
            }
        else:
            return {
                "heading": "Montserrat",
                "body": "Open Sans",
                "url": "https://fonts.google.com/share?selection.family=Montserrat|Open+Sans"
            }
    
    def format_output(self, brand_kit: Dict, logo_prompts: Dict, moodboard_prompt: str, pattern_prompt: str) -> str:
        colors = self.get_color_palette(brand_kit["personality"])
        typography = self.get_typography_pairing(brand_kit["personality"])
        
        output = f"🎨 *Brand Kit: {brand_kit['brand_name']}*\n\n"
        output += f"📋 *Brief*\n"
        output += f"• Industry: {brand_kit['industry']}\n"
        output += f"• Personality: {brand_kit['personality']}\n"
        if brand_kit['color_preference']:
            output += f"• Color preference: {brand_kit['color_preference']}\n"
        output += "\n"
        
        output += f"🎨 *Color Palette*\n"
        for role, hex_code in colors.items():
            output += f"• {role}: `{hex_code}`\n"
        output += "\n"
        
        output += f"📝 *Typography*\n"
        output += f"• Headings: {typography['heading']}\n"
        output += f"• Body: {typography['body']}\n"
        output += f"• Google Fonts: {typography['url']}\n\n"
        
        output += f"🖼️ *Logo Prompts (use /generate_brand_images)*\n"
        output += f"1. *Logo A (Wordmark)*\n"
        output += f"   `{logo_prompts['logo_a'][:80]}...`\n\n"
        output += f"2. *Logo B (Icon + Wordmark)*\n"
        output += f"   `{logo_prompts['logo_b'][:80]}...`\n\n"
        
        output += f"🎨 *Moodboard Prompt*\n"
        output += f"   `{moodboard_prompt[:80]}...`\n\n"
        
        output += f"🔲 *Pattern Prompt*\n"
        output += f"   `{pattern_prompt[:80]}...`\n\n"
        
        output += f"✨ *Next Steps:*\n"
        output += f"• Send /generate_brand_images to create visual assets\n"
        output += f"• Or use prompts manually with /image"
        
        return output
    
    def save_brand_kit(self, brand_kit: Dict, logo_prompts: Dict, moodboard_prompt: str, pattern_prompt: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kit_file = self.output_dir / f"brand_kit_{brand_kit['brand_name'].replace(' ', '_')}_{timestamp}.json"
        
        data = {
            "brief": brand_kit,
            "logo_prompts": logo_prompts,
            "moodboard_prompt": moodboard_prompt,
            "pattern_prompt": pattern_prompt,
            "color_palette": self.get_color_palette(brand_kit["personality"]),
            "typography": self.get_typography_pairing(brand_kit["personality"]),
            "status": "prompts_ready"
        }
        
        with open(kit_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return kit_file
