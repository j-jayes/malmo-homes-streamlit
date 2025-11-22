# Computer Vision Pipeline Implementation Checklist

**Date:** 2025-11-16  
**Status:** 📋 Planning Phase  
**Goal:** Extract visual features from property images to enhance price predictions

---

## 🎯 Executive Summary

Add computer vision capabilities to extract 50+ visual features from property images that affect price. This will improve ML model accuracy by ~5-7% and enable better identification of underpriced properties.

**Key Components:**
1. **Part 1:** Extend scrapers to collect image URLs (Week 1)
2. **Part 2:** Implement VLM-based feature extraction (Week 2-3)
3. **Part 3:** Integrate features into price prediction (Week 4)

**Estimated Timeline:** 4 weeks  
**Complexity:** Medium-High  
**ROI:** High (improves core value proposition)

---

## 📸 Part 1: Image Collection Pipeline

**Goal:** Extend property scrapers to collect and store property image URLs  
**Timeline:** Week 1 (5-7 days)  
**Estimated Effort:** 12-15 hours

### Task 1.1: Analyze Image URLs Structure ✅ (2h)

**Status:** ✅ COMPLETE (during initial research)

**Image URL Pattern Discovered:**
```
https://bilder.hemnet.se/images/itemgallery_cut/3f/7f/3f7f35f5764a00eb46a22ddb23e61299.jpg
https://bilder.hemnet.se/images/itemgallery_cut/3a/79/3a7956cfe12a4d8d4a9cc7ffee387797.jpg
```

**Key Findings:**
- Images hosted on `bilder.hemnet.se`
- URL pattern: `/images/itemgallery_cut/{hash}.jpg`
- Hash appears to be MD5-based unique identifier
- Typical property has 20-30 images
- Images are in gallery carousel

**Where to Find:**
- In `__NEXT_DATA__` Apollo State under `images` or `media` field
- OR in HTML `<img>` tags with `itemgallery_cut` path
- Plan view (floor plan) often separate: `/images/item_plan/`

---

### Task 1.2: Update Pydantic Schema (2h)

- [ ] Add image fields to `BaseProperty` model
- [ ] Create `PropertyImage` nested model for metadata
- [ ] Add validation for image URLs
- [ ] Update serialization/deserialization

**File:** `src/models/property_schema.py`

**Changes Needed:**

```python
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class PropertyImage(BaseModel):
    """Individual property image with metadata."""
    url: HttpUrl
    image_type: str  # "room", "exterior", "floor_plan", "other"
    order: int  # Position in gallery
    width: Optional[int] = None
    height: Optional[int] = None
    description: Optional[str] = None  # Sometimes available

class BaseProperty(BaseModel):
    # ... existing fields ...
    
    # New image fields
    image_urls: List[HttpUrl] = []  # All image URLs
    images: List[PropertyImage] = []  # Detailed image metadata
    image_count: int = 0  # Quick count
    has_floor_plan: bool = False
    floor_plan_url: Optional[HttpUrl] = None
    
    # CV features (populated later)
    visual_features: Optional[Dict[str, Any]] = None
    visual_features_confidence: Optional[float] = None
    visual_features_extracted_at: Optional[datetime] = None
```

**Validation Rules:**
- At least 1 image required for CV analysis
- Deduplicate URLs (same image sometimes appears twice)
- Filter out tiny thumbnails (<200px)

---

### Task 1.3: Update Property Scraper (4h)

- [ ] Extract image URLs from `__NEXT_DATA__`
- [ ] Parse image metadata (type, order, dimensions)
- [ ] Handle floor plans separately
- [ ] Add image extraction to `_extract_common_fields()`
- [ ] Test on sold and for-sale properties

**File:** `src/scrapers/property_detail_scraper.py`

**New Method:**

```python
def _extract_images(self, next_data: Dict, apollo_state: Dict) -> Dict:
    """Extract all property images with metadata."""
    images = []
    
    # Method 1: Try Apollo State first
    media = next_data.get('media') or next_data.get('images', [])
    
    if isinstance(media, list):
        for idx, img in enumerate(media):
            img_data = self._extract_value(img, apollo_state)
            if isinstance(img_data, dict):
                url = img_data.get('url') or img_data.get('href')
                if url and 'bilder.hemnet.se' in url:
                    images.append({
                        'url': url,
                        'order': idx,
                        'width': img_data.get('width'),
                        'height': img_data.get('height'),
                        'type': self._classify_image_type(url, img_data)
                    })
    
    # Method 2: Fallback to HTML parsing if needed
    if not images:
        page_content = self.page.content()
        soup = BeautifulSoup(page_content, 'html.parser')
        gallery_imgs = soup.find_all('img', src=re.compile(r'bilder\.hemnet\.se'))
        for idx, img in enumerate(gallery_imgs):
            images.append({
                'url': img['src'],
                'order': idx,
                'type': 'room',
            })
    
    # Extract floor plan separately
    floor_plan = None
    for img in images:
        if 'item_plan' in img['url'] or img.get('type') == 'floor_plan':
            floor_plan = img['url']
            break
    
    return {
        'images': images,
        'image_urls': [img['url'] for img in images],
        'image_count': len(images),
        'floor_plan_url': floor_plan,
        'has_floor_plan': floor_plan is not None
    }

def _classify_image_type(self, url: str, metadata: Dict) -> str:
    """Classify image type from URL or metadata."""
    if 'item_plan' in url:
        return 'floor_plan'
    # Add more classification logic
    return 'room'
```

**Integration:**
```python
def _extract_common_fields(self, next_data: Dict, coords: ...) -> Dict:
    data = {}
    # ... existing extractions ...
    
    # Extract images
    image_data = self._extract_images(next_data, apollo_state)
    data.update(image_data)
    
    return data
```

---

### Task 1.4: Add Image Download Utility (3h)

- [ ] Create `ImageDownloader` class with rate limiting
- [ ] Implement batch downloading with progress bars
- [ ] Add retry logic for failed downloads
- [ ] Cache images locally with hash-based filenames
- [ ] Optional: Resize images to standard size

**File:** `src/scrapers/image_downloader.py` (NEW)

```python
import hashlib
import requests
from pathlib import Path
from typing import List, Optional
from time import sleep
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

class ImageDownloader:
    """Download property images with rate limiting and caching."""
    
    def __init__(
        self, 
        cache_dir: Path = Path("data/images"),
        max_size: Optional[int] = 1024,  # Max dimension
        delay: float = 0.5
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
    
    def download_image(self, url: str, property_id: str) -> Optional[Path]:
        """Download single image and cache locally."""
        # Generate cache filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = self.cache_dir / property_id / f"{url_hash}.jpg"
        
        # Return if already cached
        if cache_path.exists():
            logger.debug(f"Cache hit: {cache_path}")
            return cache_path
        
        # Download
        try:
            cache_path.parent.mkdir(exist_ok=True)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Save to cache
            cache_path.write_bytes(response.content)
            logger.info(f"Downloaded: {url} → {cache_path}")
            
            # Optional: resize if needed
            if self.max_size:
                self._resize_image(cache_path, self.max_size)
            
            sleep(self.delay)
            return cache_path
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
    
    def download_batch(
        self, 
        image_urls: List[str], 
        property_id: str
    ) -> List[Path]:
        """Download all images for a property."""
        paths = []
        for url in tqdm(image_urls, desc=f"Downloading {property_id}"):
            path = self.download_image(url, property_id)
            if path:
                paths.append(path)
        return paths
    
    def _resize_image(self, path: Path, max_size: int):
        """Resize image to max dimension (preserving aspect ratio)."""
        from PIL import Image
        img = Image.open(path)
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        img.save(path, optimize=True, quality=85)
```

**Usage:**
```python
downloader = ImageDownloader(cache_dir=Path("data/images"))
images = downloader.download_batch(property.image_urls, property.property_id)
```

---

### Task 1.5: Test Image Collection (1h)

- [ ] Test on 10 sold properties
- [ ] Test on 10 active properties
- [ ] Verify all image types captured
- [ ] Check deduplication works
- [ ] Validate data integrity

**Test Script:** `scripts/test_image_collection.py`

```python
from src.scrapers.property_detail_scraper import PropertyScraper

test_urls = [
    "https://www.hemnet.se/bostad/...",  # active
    "https://www.hemnet.se/salda/...",    # sold
]

scraper = PropertyScraper(headless=True)
for url in test_urls:
    prop = scraper.scrape_property(url)
    print(f"\n{prop.address}")
    print(f"Images: {prop.image_count}")
    print(f"URLs: {prop.image_urls[:3]}...")  # First 3
    print(f"Floor plan: {prop.has_floor_plan}")
```

**Success Criteria:**
- ✅ All test properties have `image_count > 0`
- ✅ Floor plans detected when present
- ✅ No duplicate URLs
- ✅ All URLs are valid (start with `https://bilder.hemnet.se`)

---

## 🤖 Part 2: Vision Language Model Feature Extraction

**Goal:** Use VLM to extract visual features from property images  
**Timeline:** Week 2-3 (10-14 days)  
**Estimated Effort:** 20-25 hours

### Task 2.1: VLM Research & Selection (4h)

- [ ] Set up accounts/access for candidate models
- [ ] Test each model on 20 sample images
- [ ] Measure accuracy, speed, and cost
- [ ] Create comparison matrix
- [ ] Select final model(s)

**Models to Evaluate:**

1. **Moondream2** (Prototyping)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image

model_id = "vikhyatk/moondream2"
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained(model_id)

image = Image.open("property.jpg")
response = model.answer_question(
    image, 
    "Does this room have hardwood floors?",
    tokenizer
)
```

2. **LLaVA 1.6** (Production)
```python
from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration

processor = LlavaNextProcessor.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf")
model = LlavaNextForConditionalGeneration.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf")

prompt = "[INST] <image>\nAnalyze this property image... [/INST]"
inputs = processor(prompt, image, return_tensors="pt")
output = model.generate(**inputs, max_new_tokens=500)
```

3. **GPT-4V** (Validation)
```python
from openai import OpenAI
import base64

client = OpenAI()
with open("property.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Analyze this property image..."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]
    }],
    max_tokens=500
)
```

**Evaluation Metrics:**
- Accuracy on manually labeled test set (50 images)
- Processing speed (images/minute)
- Cost per 1000 images
- GPU requirements
- API reliability

**Decision Matrix:**

| Model | Accuracy | Speed | Cost/1k | GPU Needed | Best For |
|-------|----------|-------|---------|------------|----------|
| Moondream2 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $0 | No (CPU) | Prototyping |
| LLaVA 1.6 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $0 | Yes (T4) | Production |
| Qwen2-VL | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $0 | Yes (A10) | High accuracy |
| GPT-4V | ⭐⭐⭐⭐⭐ | ⭐⭐ | $10 | No (API) | Validation |

---

### Task 2.2: Prompt Engineering (6h)

- [ ] Design feature taxonomy (50+ features)
- [ ] Create prompt templates for each category
- [ ] Test different prompt structures
- [ ] Optimize for JSON output
- [ ] Validate on test set

**Feature Taxonomy:** (See detailed list in project status)

**Prompt Template Design:**

```python
SYSTEM_PROMPT = """You are an expert Swedish real estate appraiser with 20 years of experience. 
Your task is to analyze property images and identify visual features that affect market value.

Be objective and thorough. Focus on observable facts, not subjective opinions.
Respond in JSON format with confidence scores (0-100) for each feature."""

ANALYSIS_PROMPT = """Analyze this Swedish apartment image and identify the following features:

**Flooring:**
- hardwood_floor: Is there visible hardwood/parquet flooring? (yes/no/unsure)
- herringbone_pattern: Specifically herringbone parquet? (yes/no/unsure)
- flooring_condition: Good/Fair/Poor

**Kitchen (if visible):**
- modern_kitchen: Updated modern kitchen? (yes/no/unsure)
- marble_countertops: Marble or stone countertops? (yes/no/unsure)
- integrated_appliances: Built-in appliances? (yes/no/unsure)

**Natural Light:**
- light_level: High/Medium/Low natural light
- large_windows: Multiple large windows? (yes/no/unsure)
- south_facing: Appears south-facing? (yes/no/unsure)

**Condition & Style:**
- renovation_status: Newly renovated / Well maintained / Original / Needs work
- style: Scandinavian / Modern / Classic / Industrial / Mixed
- ceiling_height: Standard (~2.6m) / High (>2.8m) / Low (<2.5m)

**Special Features:**
- fireplace: Visible fireplace? (yes/no)
- exposed_brick: Exposed brick wall? (yes/no)
- moldings: Decorative moldings/cornice? (yes/no)
- built_in_storage: Custom storage solutions? (yes/no)

For each feature, provide:
1. Your assessment (yes/no/unsure or category)
2. Confidence score (0-100)
3. Brief reasoning (1 sentence)

Respond in this JSON format:
{
  "flooring": {
    "hardwood_floor": {"value": "yes", "confidence": 95, "reasoning": "Clear herringbone parquet visible"},
    ...
  },
  ...
}
"""

MULTI_IMAGE_PROMPT = """You are analyzing {image_count} images from the same apartment listing.

Task: Synthesize information across all images to create a comprehensive property assessment.

For features visible in multiple images, use the highest confidence observation.
For room-specific features (kitchen, bathroom), only assess if that room is visible.

Images: {image_descriptions}

Provide a complete property analysis in JSON format."""
```

**Prompt Optimization Techniques:**
1. **Chain-of-Thought:** Ask model to reason step-by-step
2. **Few-Shot Examples:** Include 2-3 example analyses
3. **JSON Schema:** Provide exact output structure
4. **Confidence Calibration:** Ask for uncertainty estimates
5. **Multi-Image Synthesis:** Aggregate features across photos

---

### Task 2.3: Build Feature Extractor (6h)

- [ ] Create `VisionFeatureExtractor` class
- [ ] Implement single-image analysis
- [ ] Implement multi-image aggregation
- [ ] Add confidence scoring
- [ ] Build feature validation pipeline

**File:** `src/models/vision_features.py` (NEW)

```python
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VisionFeatureExtractor:
    """Extract visual features from property images using VLM."""
    
    def __init__(
        self, 
        model_name: str = "llava-1.6",
        batch_size: int = 5,
        cache_dir: Optional[Path] = None
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self._init_model()
    
    def _init_model(self):
        """Initialize VLM model."""
        if self.model_name == "moondream2":
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.model = AutoModelForCausalLM.from_pretrained(
                "vikhyatk/moondream2",
                trust_remote_code=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained("vikhyatk/moondream2")
            self.model_type = "moondream"
            
        elif self.model_name == "llava-1.6":
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            self.processor = LlavaNextProcessor.from_pretrained(
                "llava-hf/llava-v1.6-mistral-7b-hf"
            )
            self.model = LlavaNextForConditionalGeneration.from_pretrained(
                "llava-hf/llava-v1.6-mistral-7b-hf",
                torch_dtype=torch.float16
            )
            self.model_type = "llava"
            
        elif self.model_name == "gpt-4v":
            from openai import OpenAI
            self.client = OpenAI()
            self.model_type = "openai"
        
        logger.info(f"Initialized {self.model_name} for feature extraction")
    
    def extract_features(
        self, 
        image_paths: List[Path],
        property_id: str
    ) -> Dict[str, Any]:
        """
        Extract features from all images of a property.
        
        Returns:
            Dictionary with features, confidence scores, and metadata
        """
        # Check cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{property_id}_features.json"
            if cache_file.exists():
                return json.loads(cache_file.read_text())
        
        logger.info(f"Extracting features from {len(image_paths)} images")
        
        # Analyze each image
        image_features = []
        for img_path in image_paths:
            features = self._analyze_single_image(img_path)
            if features:
                image_features.append(features)
        
        # Aggregate features across images
        aggregated = self._aggregate_features(image_features)
        
        # Add metadata
        result = {
            "property_id": property_id,
            "features": aggregated,
            "image_count": len(image_paths),
            "extracted_at": datetime.now().isoformat(),
            "model": self.model_name,
        }
        
        # Cache result
        if self.cache_dir:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(result, indent=2))
        
        return result
    
    def _analyze_single_image(self, image_path: Path) -> Optional[Dict]:
        """Analyze single image and extract features."""
        try:
            image = Image.open(image_path)
            
            if self.model_type == "moondream":
                # Use question-answering approach
                features = self._extract_moondream(image)
            elif self.model_type == "llava":
                features = self._extract_llava(image)
            elif self.model_type == "openai":
                features = self._extract_openai(image_path)
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to analyze {image_path}: {e}")
            return None
    
    def _extract_llava(self, image: Image) -> Dict:
        """Extract features using LLaVA."""
        prompt = self._build_prompt()
        inputs = self.processor(prompt, image, return_tensors="pt")
        
        output = self.model.generate(
            **inputs, 
            max_new_tokens=1000,
            do_sample=True,
            temperature=0.2
        )
        
        response = self.processor.decode(output[0], skip_special_tokens=True)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            features = json.loads(json_str)
            return features
        except:
            logger.warning("Failed to parse JSON response")
            return {}
    
    def _aggregate_features(self, image_features: List[Dict]) -> Dict:
        """
        Aggregate features across multiple images.
        
        Strategy:
        - For binary features: Use highest confidence "yes"
        - For categorical: Use most confident value
        - Calculate overall confidence score
        """
        if not image_features:
            return {}
        
        aggregated = {}
        
        # Process each feature category
        for category in ['flooring', 'kitchen', 'lighting', 'condition', 'special']:
            category_agg = {}
            
            # Collect all observations for this category
            for img_features in image_features:
                if category not in img_features:
                    continue
                    
                for feature, data in img_features[category].items():
                    if feature not in category_agg:
                        category_agg[feature] = []
                    category_agg[feature].append(data)
            
            # Aggregate each feature
            for feature, observations in category_agg.items():
                # Find highest confidence observation
                best = max(observations, key=lambda x: x.get('confidence', 0))
                aggregated[feature] = best
        
        return aggregated
    
    def _build_prompt(self) -> str:
        """Build the analysis prompt."""
        return f"[INST] <image>\n{ANALYSIS_PROMPT}[/INST]"
```

---

### Task 2.4: Batch Processing Pipeline (4h)

- [ ] Create batch processing script
- [ ] Add progress tracking and logging
- [ ] Implement checkpointing (resume capability)
- [ ] Handle errors gracefully
- [ ] Export results to structured format

**File:** `scripts/extract_visual_features.py` (NEW)

```python
#!/usr/bin/env python
"""
Batch extract visual features from property images.

Usage:
    python scripts/extract_visual_features.py --input data/raw/sold_properties.csv --limit 100
"""

import argparse
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
from src.models.vision_features import VisionFeatureExtractor
from src.scrapers.image_downloader import ImageDownloader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input CSV with properties')
    parser.add_argument('--output', default='data/processed/visual_features.json')
    parser.add_argument('--model', default='llava-1.6', choices=['moondream2', 'llava-1.6', 'gpt-4v'])
    parser.add_argument('--limit', type=int, help='Limit number of properties')
    parser.add_argument('--checkpoint-file', default='data/checkpoints/vision_extraction.pkl')
    args = parser.parse_args()
    
    # Load properties
    df = pd.read_csv(args.input)
    if args.limit:
        df = df.head(args.limit)
    
    logger.info(f"Processing {len(df)} properties with {args.model}")
    
    # Initialize
    extractor = VisionFeatureExtractor(
        model_name=args.model,
        cache_dir=Path('data/cache/vision_features')
    )
    downloader = ImageDownloader(cache_dir=Path('data/images'))
    
    # Load checkpoint if exists
    checkpoint_path = Path(args.checkpoint_file)
    if checkpoint_path.exists():
        import pickle
        with open(checkpoint_path, 'rb') as f:
            processed_ids = pickle.load(f)
        logger.info(f"Resuming from checkpoint: {len(processed_ids)} already processed")
    else:
        processed_ids = set()
    
    results = []
    
    # Process each property
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        property_id = row['property_id']
        
        # Skip if already processed
        if property_id in processed_ids:
            continue
        
        try:
            # Download images
            image_urls = eval(row['image_urls'])  # Assuming stored as string
            image_paths = downloader.download_batch(image_urls, property_id)
            
            # Extract features
            features = extractor.extract_features(image_paths, property_id)
            
            results.append({
                'property_id': property_id,
                'features': features,
                'image_count': len(image_paths)
            })
            
            # Update checkpoint
            processed_ids.add(property_id)
            if len(processed_ids) % 10 == 0:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                with open(checkpoint_path, 'wb') as f:
                    pickle.dump(processed_ids, f)
            
        except Exception as e:
            logger.error(f"Failed to process {property_id}: {e}")
            continue
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"✓ Saved {len(results)} feature extractions to {output_path}")

if __name__ == '__main__':
    main()
```

**Run Examples:**
```bash
# Prototype with Moondream on 100 properties
python scripts/extract_visual_features.py \
    --input data/raw/sold_properties.csv \
    --model moondream2 \
    --limit 100

# Production with LLaVA on all properties
python scripts/extract_visual_features.py \
    --input data/raw/sold_properties.csv \
    --model llava-1.6

# Validation with GPT-4V on 500 random sample
python scripts/extract_visual_features.py \
    --input data/raw/sold_properties_sample.csv \
    --model gpt-4v \
    --limit 500
```

---

### Task 2.5: Validation & Quality Control (3h)

- [ ] Create ground truth labeled dataset (100 images)
- [ ] Calculate accuracy metrics
- [ ] Identify common errors
- [ ] Tune confidence thresholds
- [ ] Document model limitations

**Validation Strategy:**

1. **Manual Labeling:** 
   - Select 100 diverse property images
   - Have 2-3 people independently label features
   - Resolve disagreements
   - Use as ground truth

2. **Metrics:**
   - Accuracy per feature
   - Precision/Recall for binary features
   - Confusion matrix for categorical features
   - Confidence calibration

3. **Error Analysis:**
   - False positives: Model sees features that aren't there
   - False negatives: Model misses obvious features
   - Ambiguous cases: Human labelers disagree

**Test Script:** `scripts/validate_vision_model.py`

```python
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

# Load ground truth
ground_truth = pd.read_csv('data/test/manual_labels.csv')

# Load model predictions
predictions = pd.read_json('data/test/model_predictions.json')

# Compare
for feature in ['hardwood_floor', 'modern_kitchen', 'high_natural_light']:
    y_true = ground_truth[feature]
    y_pred = predictions[feature]
    
    print(f"\n{feature}:")
    print(classification_report(y_true, y_pred))
```

---

## 💰 Part 3: Integration with Price Prediction Model

**Goal:** Add visual features to ML model and measure improvement  
**Timeline:** Week 4 (5-7 days)  
**Estimated Effort:** 15-20 hours

### Task 3.1: Feature Engineering (3h)

- [ ] Convert extracted features to model-ready format
- [ ] Handle missing values
- [ ] Create derived features
- [ ] Normalize and scale features
- [ ] Create feature importance baseline

**File:** `src/features/vision_features_processor.py` (NEW)

```python
import pandas as pd
from typing import Dict, List

class VisionFeaturesProcessor:
    """Process raw vision features for ML model."""
    
    BINARY_FEATURES = [
        'has_hardwood_floor',
        'has_herringbone_parquet',
        'has_modern_kitchen',
        'has_marble_countertops',
        'has_marble_bathroom',
        'has_fireplace',
        'has_exposed_brick',
        'has_high_ceilings',
        'has_moldings',
        'high_natural_light',
        'newly_renovated',
        'enclosed_balcony',
    ]
    
    CATEGORICAL_FEATURES = [
        'flooring_condition',     # good, fair, poor
        'renovation_status',      # new, maintained, original, needs_work
        'style',                  # scandinavian, modern, classic, industrial
    ]
    
    SCORE_FEATURES = [
        'overall_condition_score',     # 0-100
        'renovation_quality_score',    # 0-100
        'natural_light_score',         # 0-100
    ]
    
    def process_features(self, raw_features: Dict) -> pd.Series:
        """Convert raw VLM output to ML features."""
        features = {}
        
        # Binary features
        for feat in self.BINARY_FEATURES:
            features[feat] = self._extract_binary(raw_features, feat)
        
        # Categorical → one-hot
        for feat in self.CATEGORICAL_FEATURES:
            value = self._extract_categorical(raw_features, feat)
            # Create dummy variables
            for category in self._get_categories(feat):
                features[f"{feat}_{category}"] = int(value == category)
        
        # Score features
        for feat in self.SCORE_FEATURES:
            features[feat] = self._extract_score(raw_features, feat)
        
        # Derived features
        features['has_premium_finishes'] = (
            features.get('has_marble_countertops', 0) + 
            features.get('has_marble_bathroom', 0) + 
            features.get('has_herringbone_parquet', 0)
        ) >= 2
        
        features['has_character_features'] = (
            features.get('has_fireplace', 0) or
            features.get('has_exposed_brick', 0) or
            features.get('has_moldings', 0)
        )
        
        return pd.Series(features)
    
    def _extract_binary(self, raw: Dict, feature: str) -> int:
        """Extract binary feature with confidence threshold."""
        # Navigate through nested structure
        for category in raw.get('features', {}).values():
            if not isinstance(category, dict):
                continue
            for feat_name, data in category.items():
                if feat_name.lower() in feature.lower():
                    value = data.get('value', 'no')
                    confidence = data.get('confidence', 0)
                    # Only return 1 if confident yes
                    return int(value == 'yes' and confidence > 70)
        return 0
    
    def _extract_score(self, raw: Dict, feature: str) -> float:
        """Extract numeric score feature."""
        # Calculate score based on multiple indicators
        if 'condition' in feature:
            return self._calculate_condition_score(raw)
        elif 'renovation' in feature:
            return self._calculate_renovation_score(raw)
        elif 'light' in feature:
            return self._calculate_light_score(raw)
        return 50.0  # Default neutral score
```

---

### Task 3.2: Update Training Pipeline (4h)

- [ ] Merge visual features with existing dataset
- [ ] Update feature columns in model
- [ ] Retrain model with new features
- [ ] Save new model version
- [ ] Document feature additions

**File:** `src/models/train_model.py` (EXTEND EXISTING)

```python
from src.features.vision_features_processor import VisionFeaturesProcessor

def load_training_data():
    """Load and merge all features."""
    # Load base property data
    properties = pd.read_csv('data/processed/properties.csv')
    
    # Load visual features
    vision_features = pd.read_json('data/processed/visual_features.json')
    
    # Process visual features
    processor = VisionFeaturesProcessor()
    vision_df = vision_features.apply(
        lambda row: processor.process_features(row['features']),
        axis=1
    )
    
    # Merge
    df = properties.merge(
        vision_df,
        left_on='property_id',
        right_index=True,
        how='left'
    )
    
    # Fill missing visual features with 0 (no info)
    vision_cols = processor.get_all_feature_names()
    df[vision_cols] = df[vision_cols].fillna(0)
    
    return df

# Train model
df = load_training_data()
X = df.drop(['final_price'], axis=1)
y = df['final_price']

# ... rest of training code ...
```

---

### Task 3.3: Model Evaluation & Comparison (4h)

- [ ] Train baseline model (no vision features)
- [ ] Train full model (with vision features)
- [ ] Compare R², MAE, RMSE
- [ ] Analyze feature importance
- [ ] Create comparison report

**Evaluation Script:** `scripts/evaluate_vision_impact.py`

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import numpy as np

# Split features
base_features = [
    'rooms', 'living_area', 'floor', 'building_year',
    'association_fee', 'has_elevator', 'has_balcony'
]

vision_features = processor.get_all_feature_names()

# Baseline model (no vision)
model_baseline = RandomForestRegressor(n_estimators=100)
model_baseline.fit(X_train[base_features], y_train)

y_pred_baseline = model_baseline.predict(X_test[base_features])
r2_baseline = r2_score(y_test, y_pred_baseline)
mae_baseline = mean_absolute_error(y_test, y_pred_baseline)

# Full model (with vision)
model_full = RandomForestRegressor(n_estimators=100)
model_full.fit(X_train[base_features + vision_features], y_train)

y_pred_full = model_full.predict(X_test[base_features + vision_features])
r2_full = r2_score(y_test, y_pred_full)
mae_full = mean_absolute_error(y_test, y_pred_full)

# Comparison
print(f"""
Model Performance Comparison
{'='*50}

Baseline (No Vision):
  R² Score:  {r2_baseline:.4f}
  MAE:       {mae_baseline:,.0f} SEK
  RMSE:      {np.sqrt(mean_squared_error(y_test, y_pred_baseline)):,.0f} SEK

Full Model (With Vision):
  R² Score:  {r2_full:.4f} (+{r2_full - r2_baseline:+.4f})
  MAE:       {mae_full:,.0f} SEK ({mae_full - mae_baseline:+,.0f})
  RMSE:      {np.sqrt(mean_squared_error(y_test, y_pred_full)):,.0f} SEK

Improvement:
  R² Increase: {(r2_full - r2_baseline) / r2_baseline * 100:.1f}%
  MAE Decrease: {(mae_baseline - mae_full) / mae_baseline * 100:.1f}%
""")

# Feature importance for vision features
importances = pd.DataFrame({
    'feature': base_features + vision_features,
    'importance': model_full.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTop 10 Most Important Vision Features:")
vision_importances = importances[importances['feature'].isin(vision_features)]
print(vision_importances.head(10))
```

**Success Criteria:**
- ✅ R² improves by at least 3% (e.g., 0.80 → 0.83)
- ✅ MAE decreases by at least 50,000 SEK
- ✅ At least 5 vision features in top 20 by importance
- ✅ No regression on baseline performance

---

### Task 3.4: A/B Testing on Live Data (2h)

- [ ] Select test set of recent listings
- [ ] Generate predictions with both models
- [ ] Compare to actual sale prices (when available)
- [ ] Calculate accuracy by property segment
- [ ] Document findings

**Test Strategy:**

1. **Holdout Set:** Reserve last 3 months of sales
2. **Predictions:** Generate with both models
3. **Wait:** Let properties sell naturally
4. **Compare:** Which model was more accurate?

**Segments to Analyze:**
- High-end properties (>5M SEK)
- Renovated properties
- Properties with unique features
- Standard apartments

---

### Task 3.5: Deploy Updated Model (2h)

- [ ] Save model with version tag
- [ ] Update prediction API
- [ ] Create model card documentation
- [ ] Deploy to production environment
- [ ] Monitor performance

**Model Versioning:**

```python
import joblib
from datetime import datetime

# Save model
version = f"v2.0_vision_{datetime.now().strftime('%Y%m%d')}"
joblib.dump(model_full, f'models/housing_price_model_{version}.joblib')

# Save feature list
with open(f'models/features_{version}.txt', 'w') as f:
    f.write('\n'.join(base_features + vision_features))

# Create model card
model_card = {
    "version": version,
    "created_at": datetime.now().isoformat(),
    "features": {
        "base": len(base_features),
        "vision": len(vision_features),
        "total": len(base_features) + len(vision_features)
    },
    "performance": {
        "r2_score": r2_full,
        "mae": mae_full,
        "rmse": np.sqrt(mean_squared_error(y_test, y_pred_full))
    },
    "training_data": {
        "properties": len(X_train),
        "date_range": "2020-01 to 2025-11"
    }
}

with open(f'models/model_card_{version}.json', 'w') as f:
    json.dump(model_card, f, indent=2)
```

---

## 📊 Success Metrics & KPIs

### Part 1: Image Collection
- ✅ 95%+ of properties have images
- ✅ Average 20+ images per property
- ✅ <1% broken/invalid URLs
- ✅ Floor plans captured for 80%+ properties

### Part 2: Feature Extraction
- ✅ 90%+ accuracy on manually labeled test set
- ✅ Process 100 properties/hour (with GPU)
- ✅ Confidence scores available for all features
- ✅ <5% extraction failures

### Part 3: Model Integration
- ✅ R² improves by 3-7% (0.80 → 0.83-0.87)
- ✅ MAE decreases by 50-100k SEK
- ✅ Vision features in top 20 by importance
- ✅ No performance regression on any segment

---

## 💰 Cost Estimation

### Development
- **Time:** 4 weeks × 40 hours = 160 hours
- **Infrastructure:** GPU for LLaVA (Google Colab or Cloud)
  - Colab Pro: $10/month
  - GCP T4: ~$0.35/hour × 40 hours = $14

### Production (Monthly)
- **Image Storage:** Minimal (URLs only)
- **Feature Extraction:** 
  - LLaVA: Free (self-hosted)
  - GPT-4V validation: $10/month (10% sample)
- **Model Training:** <$5/month compute

**Total Monthly Cost:** $25-30

**ROI:** Improved predictions → Better property identification → Higher user value

---

## 🚀 Deployment Strategy

### Phase 1: Prototype (Week 1-2)
- Build with Moondream2 (fast, free)
- Validate approach on 100 properties
- Iterate on prompts

### Phase 2: Production (Week 3)
- Deploy LLaVA 1.6 on GPU
- Process all historical properties
- Validate with GPT-4V sample

### Phase 3: Integration (Week 4)
- Merge into ML pipeline
- A/B test predictions
- Deploy to production

### Phase 4: Monitoring (Ongoing)
- Track prediction accuracy
- Monitor feature quality
- Retrain quarterly

---

## 📝 Documentation Requirements

- [ ] Update README with vision features
- [ ] Create vision pipeline architecture diagram
- [ ] Document prompt templates
- [ ] Write feature extraction guide
- [ ] Create model comparison report
- [ ] Add example notebooks

---

## ✅ Checklist Summary

### Week 1: Image Collection
- [x] Research image URL structure ✅
- [ ] Update Pydantic schema
- [ ] Extend property scraper
- [ ] Build image downloader
- [ ] Test on sample properties

### Week 2: VLM Setup
- [ ] Evaluate candidate models
- [ ] Design prompt templates
- [ ] Build feature extractor
- [ ] Create batch processing pipeline
- [ ] Validate on test set

### Week 3: Feature Extraction
- [ ] Process all historical properties
- [ ] Extract features from active listings
- [ ] Quality control and validation
- [ ] Export to structured format

### Week 4: Model Integration
- [ ] Engineer ML features
- [ ] Retrain price prediction model
- [ ] Evaluate performance improvement
- [ ] A/B test on live data
- [ ] Deploy to production

---

**Next Actions:**
1. Review and approve this plan
2. Set up development environment (GPU access)
3. Start with Task 1.2 (Update Pydantic Schema)
4. Create feature branch: `feature/computer-vision-pipeline`

**Questions for Discussion:**
- GPU infrastructure: Colab Pro vs GCP vs local?
- Model choice: Start with Moondream or jump to LLaVA?
- Budget: Willing to use GPT-4V for validation?
- Timeline: Can we compress to 3 weeks?
