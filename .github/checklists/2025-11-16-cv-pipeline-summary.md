# Computer Vision Pipeline - Executive Summary

**Date:** 2025-11-16  
**Author:** AI Assistant (with human oversight)  
**Status:** 📋 Ready for Implementation

---

## 🎯 Vision

Add computer vision capabilities to extract 50+ visual features from property images (hardwood floors, modern kitchen, natural light, etc.) to improve price prediction accuracy by 5-7%.

---

## 🏗️ Architecture Overview

```
Property Images (Hemnet)
         ↓
  Image Collection
    (URLs + metadata)
         ↓
  Vision Language Model
   (LLaVA / GPT-4V)
         ↓
  Feature Extraction
   (50+ visual features)
         ↓
   ML Model Training
  (Traditional + Vision)
         ↓
   Price Predictions
    (More Accurate!)
```

---

## 📋 Three-Part Implementation

### Part 1: Image Collection (Week 1) 
**Goal:** Extract image URLs from property pages  
**Effort:** 12-15 hours

**Key Tasks:**
1. Update Pydantic schema with image fields
2. Modify property scraper to capture image URLs
3. Build image downloader with caching
4. Test on sample properties

**Deliverables:**
- Updated `property_schema.py`
- Extended `property_detail_scraper.py`
- New `image_downloader.py`
- Images stored in `data/images/{property_id}/`

---

### Part 2: Feature Extraction (Week 2-3)
**Goal:** Use VLM to extract visual features  
**Effort:** 20-25 hours

**Key Tasks:**
1. Select VLM (Moondream → LLaVA → GPT-4V validation)
2. Design 50+ feature taxonomy
3. Build feature extractor with confidence scores
4. Batch process all properties
5. Quality validation

**Technology Stack:**
- **Moondream2:** Prototyping (CPU, fast, free)
- **LLaVA 1.6:** Production (GPU, accurate, free)
- **GPT-4V:** Validation (API, very accurate, $10/month)

**Features to Extract:**
- Flooring: Hardwood, herringbone, condition
- Kitchen: Modern, marble counters, island
- Bathroom: Modern, marble, walk-in shower
- Lighting: Natural light level, window size
- Condition: Renovation status, maintenance
- Style: Scandinavian, modern, classic
- Special: Fireplace, exposed brick, moldings

**Deliverables:**
- New `vision_features.py` module
- Batch processing script
- Features stored as JSON per property
- Validation report

---

### Part 3: Model Integration (Week 4)
**Goal:** Add features to ML model, measure improvement  
**Effort:** 15-20 hours

**Key Tasks:**
1. Feature engineering (convert to ML format)
2. Retrain model with vision features
3. Compare baseline vs enhanced model
4. A/B test on live data
5. Deploy to production

**Expected Improvements:**
- R² Score: 0.80 → 0.83-0.87 (+3-7%)
- MAE: Decrease by 50-100k SEK
- Better predictions for renovated/high-end properties

**Deliverables:**
- Updated training pipeline
- Model comparison report
- Deployed model v2.0
- Feature importance analysis

---

## 🎨 Visual Features Taxonomy

### 50+ Features Organized by Category

**Flooring** (6 features)
- Hardwood floor, herringbone parquet, laminate
- Flooring condition (good/fair/poor)

**Kitchen** (7 features)
- Modern kitchen, marble counters, integrated appliances
- Kitchen island, open layout

**Bathroom** (5 features)
- Modern bathroom, marble, walk-in shower
- Bathtub, double sinks

**Style** (5 features)
- Scandinavian, modern, classic, industrial, minimalist

**Condition** (4 features)
- Newly renovated, well-maintained, needs work

**Lighting** (4 features)
- High natural light, bright rooms, large windows

**Balcony** (4 features)
- Enclosed balcony, French balcony, spacious, terrace

**Special** (10+ features)
- Fireplace, exposed brick, high ceilings, moldings
- View, built-in storage, etc.

---

## 🤖 VLM Comparison Matrix

| Model | Accuracy | Speed | Cost/1k | GPU | Best For |
|-------|----------|-------|---------|-----|----------|
| **Moondream2** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Free | No | Prototyping |
| **LLaVA 1.6** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Free | Yes | Production |
| **Qwen2-VL** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Free | Yes | High accuracy |
| **GPT-4V** | ⭐⭐⭐⭐⭐ | ⭐⭐ | $10 | No | Validation |

**Recommended:** LLaVA 1.6 for production + GPT-4V for 10% validation sample

---

## 💰 Cost & Resource Analysis

### Development Costs
- **Time:** 4 weeks (160 hours)
- **GPU:** Google Colab Pro ($10/month) or GCP T4 ($14 for 40 hours)
- **APIs:** OpenAI validation ($10/month)
- **Total:** ~$25-30/month

### Data Volume
- **Historical:** 56k properties × 25 images = 1.4M images
- **Active:** 500 properties × 25 images = 12.5k images
- **Storage:** URLs only (minimal), features as JSON (~5KB/property)

### Production Costs
- **Feature extraction:** Free (LLaVA self-hosted)
- **Validation:** $10/month (GPT-4V on 10% sample)
- **Storage:** <$5/month
- **Total:** $15-20/month

**ROI:** Better predictions → Find underpriced properties → High value to users

---

## 📊 Success Metrics

### Part 1: Image Collection
- ✅ 95%+ properties have images
- ✅ Average 20+ images per property
- ✅ <1% broken URLs
- ✅ Floor plans captured (80%+)

### Part 2: Feature Extraction
- ✅ 90%+ accuracy on test set
- ✅ 100 properties/hour with GPU
- ✅ Confidence scores for all features
- ✅ <5% extraction failures

### Part 3: Model Integration
- ✅ R² improves 3-7% (0.80 → 0.83-0.87)
- ✅ MAE decreases 50-100k SEK
- ✅ Vision features in top 20 importance
- ✅ No performance regression

---

## 🚀 Implementation Roadmap

### Phase 1: Research & Setup (✅ Complete)
- [x] Analyze Hemnet image structure
- [x] Research VLM options
- [x] Create implementation plan
- [x] Design feature taxonomy

### Phase 2: Image Pipeline (Week 1)
- [ ] Update property schema
- [ ] Extend scraper for images
- [ ] Build image downloader
- [ ] Test on 50 properties

### Phase 3: VLM Deployment (Week 2-3)
- [ ] Set up LLaVA on GPU
- [ ] Design & test prompts
- [ ] Build batch processor
- [ ] Extract features from all properties
- [ ] Validate accuracy

### Phase 4: Model Training (Week 4)
- [ ] Engineer features for ML
- [ ] Train baseline + enhanced models
- [ ] Compare performance
- [ ] A/B test predictions
- [ ] Deploy to production

---

## 🔬 Sample Prompt

```
You are an expert Swedish real estate appraiser. 
Analyze this apartment image and identify visual features 
that affect property value.

For each feature, provide:
1. Assessment (yes/no/unsure or category)
2. Confidence score (0-100)
3. Brief reasoning (1 sentence)

Categories to analyze:
- Flooring type and quality
- Kitchen style and condition
- Natural light level
- Renovation status
- Special features

Respond in JSON format.
```

**Example Output:**
```json
{
  "flooring": {
    "hardwood_floor": {
      "value": "yes",
      "confidence": 95,
      "reasoning": "Clear herringbone parquet visible in main room"
    }
  },
  "kitchen": {
    "modern_kitchen": {
      "value": "yes",
      "confidence": 85,
      "reasoning": "Contemporary white cabinets with integrated appliances"
    }
  },
  "lighting": {
    "high_natural_light": {
      "value": "yes",
      "confidence": 90,
      "reasoning": "Large south-facing windows visible"
    }
  }
}
```

---

## 📚 Key Findings from Research

### From Web Research (Nov 2025)

**1. Vision Language Models are Mature**
- GPT-4V, LLaVA, Qwen-VL perform well on real estate
- Open-source options (LLaVA) match commercial quality
- Models understand Swedish property features

**2. Image Similarity Techniques**
- FAISS for fast image search
- Embedding-based similarity works well
- Could enable "find similar properties" feature

**3. Best Practices**
- Use structured prompts with JSON output
- Aggregate features across multiple images
- Validate with confidence scores
- Start with small models, scale up

### Property Image Insights

**Hemnet Image Structure:**
- Images at `bilder.hemnet.se/images/itemgallery_cut/`
- Typically 20-30 images per property
- High quality (800-1200px)
- Floor plans often included
- Images stored in `__NEXT_DATA__` Apollo State

---

## 🎯 Strategic Value

### Why This Matters

1. **Better Predictions:** Vision features capture quality signals that traditional features miss
2. **Competitive Advantage:** Few property platforms use computer vision
3. **User Trust:** More accurate predictions → better recommendations
4. **Scalability:** Automated feature extraction (no manual labeling)
5. **Data Moat:** Proprietary visual feature database

### Use Cases Beyond Price Prediction

1. **Visual Search:** "Find properties with hardwood floors and modern kitchens"
2. **Quality Scoring:** Overall property condition score
3. **Renovation Detection:** Identify recently renovated properties
4. **Style Matching:** Find properties matching user's aesthetic preferences
5. **Alerts:** Notify when high-quality property listed below market

---

## 📖 Documentation Created

1. **Project Status Update** (`2025-11-15-PROJECT-STATUS.md`)
   - Added Component 4: Computer Vision
   - Updated timeline with Month 3
   - Added Phase 4 details

2. **Implementation Checklist** (`2025-11-16-computer-vision-pipeline-checklist.md`)
   - Detailed task breakdown
   - Code examples for each part
   - Validation strategies
   - 47 pages, production-ready

3. **Executive Summary** (this document)
   - High-level overview
   - Quick reference guide
   - Strategic context

---

## 🚦 Next Steps

### Immediate Actions
1. **Review Plans:** Team reviews this document
2. **GPU Setup:** Get access to T4/A10 GPU (Colab Pro or GCP)
3. **Start Development:** Begin with Task 1.2 (Update Pydantic Schema)
4. **Create Branch:** `feature/computer-vision-pipeline`

### Decision Points
- [ ] **Model Choice:** Moondream for prototype or jump to LLaVA?
- [ ] **GPU Provider:** Colab Pro vs GCP vs local machine?
- [ ] **Budget:** Approve $30/month for GPT-4V validation?
- [ ] **Timeline:** Aggressive 3 weeks or comfortable 4 weeks?

### Team Assignments
- **Data Engineer:** Part 1 (Image Collection)
- **ML Engineer:** Part 2 (Feature Extraction)
- **Data Scientist:** Part 3 (Model Integration)

---

## 🎉 Expected Impact

**Before (Baseline):**
- R² Score: 0.80
- MAE: 250k SEK
- Features: 15-20 traditional features
- Accuracy: Good for standard properties

**After (With Computer Vision):**
- R² Score: 0.85 (+6%)
- MAE: 180k SEK (-28%)
- Features: 65-70 (traditional + vision)
- Accuracy: Excellent for all property types

**Real-World Impact:**
- Better identification of underpriced properties
- More accurate valuations for renovated homes
- Competitive advantage in Swedish market
- Foundation for visual search features

---

## 💡 Innovation Highlights

This project represents cutting-edge application of:
- **Vision Language Models** for real estate
- **Multi-image aggregation** techniques
- **Structured feature extraction** with confidence scores
- **Hybrid ML** (traditional + vision features)

Few competitors are doing this in the Swedish market. This positions the project as a technical leader.

---

**Status:** Ready to implement! 🚀  
**Next Review:** After Part 1 complete (Week 1)
