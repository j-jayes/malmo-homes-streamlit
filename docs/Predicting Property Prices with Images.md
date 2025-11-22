

# **A Technical Framework for Multimodal Real Estate Valuation: Integrating Visual, Tabular, and Spatial Data for the Swedish Market**

## **Abstract**

This report presents a comprehensive technical framework for developing a machine learning (ML) model to predict Swedish apartment prices using advertisement images as a primary input. The analysis establishes this task as a multimodal supervised regression problem, which stands in contrast to traditional hedonic pricing models that rely solely on tabular data. The core technical challenge is identified as the optimal representation and fusion of heterogeneous data streams: (1) structured tabular features (e.g., square footage, location, number of rooms); (2) high-dimensional visual features extracted from property images, processed via Convolutional Neural Networks (CNNs); and (3) advanced spatial-context features derived from Graph Neural Networks (GNNs) that model neighborhood dependencies. An in-depth review of the academic literature is conducted, detailing two complementary visual feature extraction methodologies: *explicit feature tagging* (e.g., room identification, material classification) and *implicit feature embedding* (e.g., quantification of aesthetic appeal, quality, and condition).

The report surveys state-of-the-art fusion architectures, documenting the evolution from simple baseline models, such as intermediate concatenation, to advanced cross-modal attention mechanisms that dynamically weigh the influence of different modalities. Critically, this analysis introduces and addresses two non-obvious, high-impact project risks. The first is the *data integrity problem*, wherein real estate images are compromised by systemic lens distortion (e.g., wide-angle lenses) and, more recently, by generative AI for "virtual staging," which constitutes a form of data poisoning. A data forensics pre-processing pipeline is proposed to mitigate this. The second is the *data acquisition problem* specific to the Swedish market, where the publicly advertised 'listing price' ('utgångspris') is an unreliable marketing variable, and the true target label, the 'final sale price' ('slutpris'), must be acquired through a separate, longitudinal data collection process. Finally, these findings are synthesized into a proposed "Trimodal Gated-Attention" architecture, presented as a robust, production-grade model for accurate and reliable property valuation.

---

## **Part 1: The Foundations of Visual-Based Property Valuation**

### **Section 1.1: Confirming the Approach: Price Prediction as a Supervised Regression Task**

The fundamental objective of the proposed project—to predict property prices based on a set of inputs— squarely places it within the domain of **supervised machine learning**.1 In a supervised learning paradigm, a model learns to map input features to an output label by training on a dataset of examples where the "correct" answer is already known.1 The query specifically concerns the prediction of price, which is a continuous numerical value, not a discrete category. Therefore, the task is one of **regression**, not classification.1

The academic literature on asset price prediction, whether for stocks or real estate, confirms a well-established toolkit of regression algorithms.3 For projects utilizing structured, tabular data (e.g., number of rooms, square footage), common and powerful baseline models include Linear Regression, Support Vector Regression (SVR) (a variant of Support Vector Machines (SVM) for regression), Random Forests, and Gradient Boosting machines (such as XGBoost).1 These models are frequently used as benchmarks due to their high performance and interpretability.4

However, the user's explicit desire to incorporate *images* fundamentally alters the problem's nature and complexity. Traditional real estate valuation, known as hedonic price modeling, was confined to a single modality: structured tabular data.5 The inclusion of images, alongside textual descriptions and tabular data, transforms the project into a **multimodal supervised learning** task.9

This distinction is not trivial; it dictates the entire project architecture. The central technical challenge is no longer just *prediction*—which can be handled by a simple regression head—but *representation and fusion*.10 The project must answer how to effectively and cohesively combine data from fundamentally different domains: the structured numbers of a table, the high-dimensional pixel arrays of images, and the semantic content of text.10 This requirement moves the project's scope beyond simple scikit-learn models 14 and necessitates a complex, deep-learning-based multimodal framework capable of integrating diverse data sources.12

---

## **Part 2: The Swedish Data Acquisition Challenge: From 'Annons' to 'Slutpris'**

Before any model can be built, a robust and, critically, *correct* dataset must be acquired. This represents the single greatest practical hurdle for a project focused on the Swedish market.

### **Section 2.1: Navigating the Swedish Market: Hemnet, Booli, and Data Availability**

The primary sources for Swedish property data are the two dominant online portals: **Hemnet** and **Booli**.17 Hemnet is the largest marketplace, while Booli operates as a powerful aggregator.17 Automated scraping tools and commercial services are available to extract a wealth of property attributes from these platforms, including housing type, address, number of rooms, living area, and listing descriptions.19

An analysis of the platforms reveals important differences for a data collection strategy. Booli, which is free for brokers to list on, aggregates listings from a wide array of sources, including brokers' own websites. This means it often captures "kommande" (coming soon) listings before they are formally posted on Hemnet.18 Hemnet, conversely, charges significant fees for listings (reported to be between 5,500 and 10,000 SEK), which can result in a slight delay before a property appears there.18 For comprehensive data, a strategy that monitors both portals is ideal.

However, case studies from researchers who have attempted this highlight the difficulty of amassing a large-scale dataset, which is a significant concern for data-hungry deep learning models. One project scraping Hemnet for villas, after basic processing and removal of NaN values, was left with only 2,214 complete entries, a number described as a "worrying low amount of data".22 Another project, which pivoted to price prediction after failing to find public data for its initial goal (rental queue points), also noted the challenges of working with a "small dataset" scraped from Hemnet.23 This scarcity makes techniques like transfer learning (discussed in Part 4\) a necessity, not an option.

### **Section 2.2: The Critical Target Variable: Why 'Listing Price' Is Insufficient and 'Slutpris' Is Essential**

A model trained using the 'listing price' ('utgångspris') found in the initial property advertisements would be a complete and critical failure. Such a model would not predict the property's market value; it would merely predict the broker's marketing strategy.

The academic research on the Swedish housing market is unequivocal on this point. The 'utgångspris' is a *marketing tool*, not an objective valuation. Brokers, particularly in competitive markets like Stockholm, systematically engage in "underpricing".24 This practice, often referred to as 'lockpriser' (bait prices), is designed to attract a larger pool of potential buyers to the subsequent auction, which is the standard sales process in Sweden.24

The true market value of the property is determined *only* at the conclusion of this bidding process. The resulting **'slutpris' (final sale price)** is the *only* valid target variable (label) for a supervised regression model.26 The delta between 'utgångspris' and 'slutpris' can be substantial and highly variable, rendering the listing price an unreliable and misleading feature for valuation modeling.24

This distinction creates a non-obvious and significant data engineering challenge. The features (images, tabular data, listing price) are available at the *start* of the sales process, but the target label ('slutpris') is only available *after* the sale is complete. This necessitates a **two-stage longitudinal data acquisition strategy**:

1. **Stage 1: Feature and Ad Capture (Active Listings):** The system must continuously scrape active listings from Hemnet and Booli.19 For each property, it must capture and store all available input features: all tabular data (size, rooms, location, fees), all image URLs, and the full text of the description. This data is stored in a database, indexed by a unique property identifier.  
2. **Stage 2: Label Capture (Sold Listings):** The system must then continuously monitor the "sold" sections of these portals. Booli, for example, provides extensive historical 'slutpriser' data.21 Data can also be sourced from broker-wide databases like Svensk Mäklarstatistik.27 When a property from Stage 1 is found in the "sold" data, its 'slutpris' is scraped and joined to the feature set in the database, completing the labeled training example.

This two-stage imperative means the project is not a simple one-off data pull. It requires a persistent, stateful, and robust data collection infrastructure capable of tracking properties over time, from listing to sale.

### **Table 1: Data Acquisition Strategy for the Swedish Market**

| Data Point | Source (Sweden-Specific) | Data Type | Acquisition Stage | Purpose in Model |
| :---- | :---- | :---- | :---- | :---- |
| **Tabular Features** | Hemnet/Booli Active Listing Page | Tabular (Numeric, Categorical) | Stage 1: Feature Capture | Input Features ($X\_{tabular}$) |
| (e.g., *kvm*, *rum*, *avgift*) |  |  |  |  |
| **Image URLs** | Hemnet/Booli Active Listing Page | URL (links to images) | Stage 1: Feature Capture | Input Features ($X\_{image}$) |
| **Listing Description** | Hemnet/Booli Active Listing Page | Text (String) | Stage 1: Feature Capture | Input Features ($X\_{text}$) |
| **Geospatial Data** | Hemnet/Booli Active Listing Page | Tabular (Lat/Lon) | Stage 1: Feature Capture | Input Features ($X\_{spatial}$) |
| **Listing Price** | Hemnet/Booli Active Listing Page | Continuous (SEK) | Stage 1: Feature Capture | Input Feature (potential) |
| (*Utgångspris*) |  |  |  | *Not* the target label |
| **Final Sale Price** | Booli 'Slutpriser' Page | Continuous (SEK) | **Stage 2: Label Capture** | **Target Label ($y$)** |
| (*Slutpris*) | Svensk Mäklarstatistik 27 |  |  |  |

---

## **Part 3: Decoding the Image: What Visual Features Predict Price?**

This part directly addresses the core query: "What features would we want to extract?" The research provides two distinct, yet highly complementary, answers. These approaches can be broadly categorized as *explicit* (what we can see and name) and *implicit* (the overall quality we perceive).

### **Section 3.1: Explicit Feature Extraction: Identifying and Tagging Rooms, Materials, and Amenities**

This first approach uses computer vision models to perform explicit, human-understandable tasks: classification and object detection. The goal is to "tag" images with concrete, factual information about the property's tangible assets.28 This process effectively converts unstructured image data into new, high-value structured features.

This pipeline would be trained to perform several tasks:

* **Room Identification:** Classifying each image into a specific room category, such as "kitchen," "bathroom," "living room," "bedroom," or "balcony".28  
* **Amenity Detection:** Using object detection to identify specific high-value (or low-value) items within the rooms. Examples include detecting a *fireplace*, *pool*, *kitchen island*, *hardwood floors*, or *outdated appliances*.28  
* **Material and Quality Assessment:** This involves a more granular classification to identify building materials, which are strong price indicators. For example, a model could be trained to distinguish *flooring materials* (e.g., parquet, laminate, tile) or *kitchen countertop materials* (e.g., granite, quartz, laminate).29

This approach is already being operationalized in production environments. Major real estate portals like Realtor.com have developed GPU-powered, real-time APIs using advanced models such as OpenAI's CLIP and Google's Vision Transformer (ViT) to automatically generate "highly accurate and descriptive tags" for their listing images.31

The output of this entire "explicit" pipeline is not a price prediction itself. Instead, it is an "image-to-tabular" conversion process. The model generates a new set of columns to be *added* to the traditional tabular dataset (e.g., has\_balcony: 1, kitchen\_style: 'modern', flooring\_material: 'parquet'). This newly *augmented* tabular dataset can then be fed into a standard, highly interpretable, and powerful regression model like XGBoost 7 or a Random Forest.6 This architecture is often simpler to build, debug, and interpret than a fully end-to-end deep learning model.

### **Section 3.2: Implicit Feature Extraction: Using CNNs to Quantify Aesthetics, Quality, and Condition**

This second approach is more abstract and, in many ways, more powerful. It is based on the economic premise that a property's value is driven not just by its *inventory* of features (e.g., it *has* a kitchen), but by its *intangible* qualities: its overall aesthetic appeal, perceived quality, and physical condition.32

Research has consistently shown that these subjective qualities are highly predictive of price. Studies have quantified the price impact of "attractiveness" 35, "perceived safety" 33 from street-view images, "luxury levels" 33, and "building condition".33 In some cases, these visual features have been shown to carry more predictive power than some traditional, structured metadata features.35

**Convolutional Neural Networks (CNNs)** are the ideal tool for this task.16 By design, CNNs excel at "parsing complex patterns in unstructured data" 15 and can be trained to "learn a high-level representation" 32 that quantifies these nuanced, subjective qualities. Instead of outputting a tag like "kitchen," the CNN outputs a dense vector—a series of numbers—that numerically represents its assessment of the image's quality and style.

Numerous studies have validated this approach, demonstrating that hybrid models incorporating these *latent visual features* (the CNN's vector output) consistently outperform models that rely on tabular data alone.15 Notably, at least one study has been conducted on the Swedish market (specifically, apartments in Stockholm) that successfully used this multimodal approach, combining apartment features with neural networks.10

These two approaches, explicit and implicit, are not mutually exclusive; they are complementary. A state-of-the-art system should capture *both*. The explicit features explain the *inventory* of the apartment (e.g., has\_fireplace \= True). The implicit features explain the *quality* and *condition* of that inventory (e.g., a latent vector that represents "charming, well-maintained, high-end fireplace"). This combination is what allows a model to differentiate between a "newly renovated, designer kitchen" and a "dilapidated, 1970s-era kitchen," both of which would be tagged as "kitchen" by the explicit model but would receive vastly different implicit feature vectors and, consequently, have vastly different impacts on the final price prediction.

### **Table 2: Visual Feature Engineering Approaches**

| Approach | Extracted Feature | CV Technique | Model Role | Pros & Cons |
| :---- | :---- | :---- | :---- | :---- |
| **Explicit ("Tagging")** | Tangible, objective attributes: \- 'balcony', 'kitchen' 28 \- 'fireplace', 'pool' 28 \- 'parquet', 'granite' 30 | Object Detection (e.g., YOLO) Image Classification (e.g., ResNet-Classifier 31) | "Image-to-Tabular" Converter: Generates new columns for an augmented tabular dataset. | **Pros:** Highly interpretable, verifiable, easy to integrate with simpler models (e.g., XGBoost). **Cons:** Misses holistic quality, "style," or "condition." |
| **Implicit ("Scoring")** | Latent, subjective qualities: \- 'Aesthetic score' 32 \- 'Luxury level' 33 \- 'Condition' 33 \- 'Attractiveness' 35 | CNN Feature Embedding (e.g., ResNet-Encoder 32) | "Image-to-Vector" Converter: Generates a dense, latent vector for multimodal fusion. | **Pros:** Captures holistic quality and intangible value. Highly powerful. **Cons:** "Black box" nature 36, less interpretable, requires a deep learning fusion model. |

---

## **Part 4: The Computer Vision Toolkit: Architectures for Feature Extraction**

To implement the *implicit feature extraction* strategy, a powerful computer vision model is required. Given the data scarcity endemic to this problem 22, training a large CNN from scratch is computationally infeasible and virtually guaranteed to overfit.

### **Section 4.1: The Power of Transfer Learning: Using ResNet, VGG, and Vision Transformers (ViT) as Feature Encoders**

The solution to the small-data problem is **Transfer Learning**.40 This technique involves adopting a model architecture that has already been pre-trained on a massive, general-purpose image dataset, such as ImageNet, which contains millions of images across a thousand categories.39

The logic is that these models have already learned a robust, hierarchical representation of the visual world. Their early layers learn to detect universal building blocks (e.g., edges, corners, textures), while deeper layers learn to combine these into complex shapes and objects.32 This learned knowledge is highly transferable to other computer vision tasks, including real estate appraisal.40 Instead of learning from a blank slate, the model leverages this vast pre-existing knowledge.

A wide variety of pre-trained models are available. While early architectures like AlexNet and VGG are still functional 39, comparative studies in other complex domains (like medical imaging or waste classification) consistently show that more modern architectures offer superior performance. Specifically, **ResNet** (Residual Networks) 39 and **GoogLeNet** (Inception) have demonstrated higher accuracy and better feature extraction capabilities than their predecessors.42 ResNet-50 is a widely used, powerful, and robust baseline for such tasks.43 In production systems, even more recent, non-CNN architectures like the **Vision Transformer (ViT)** are being deployed for their state-of-the-art performance.31

### **Section 4.2: Anatomy of a Visual Feature: From Raw Image to a Dense Vector Representation**

This section details the practical implementation of using a pre-trained model as a "feature encoder" to generate the implicit visual vector for each image. This process treats the sophisticated CNN as a static, pre-processing step to "vectorize" the images.

The process is as follows:

1. **Load Pre-trained Model:** An architecture, such as ResNet-50, is loaded with weights pre-trained on ImageNet.39  
2. **Freeze Weights:** The model's parameters, particularly in the deep convolutional base, are "frozen." This prevents them from being updated during training, preserving the rich features learned from ImageNet.  
3. **Remove Classifier Head:** The final layer (or layers) of the network is removed. In ResNet-50, this is the 1000-class *softmax* classifier used for the ImageNet task.41  
4. **Extract Feature Vector:** The model is fed a property image. The output of the layer *just before* the removed classifier (e.g., the global average pooling layer in ResNet) is captured. This output is a high-dimensional **feature vector** (e.g., 2048 dimensions for ResNet-50).

This vector *is* the implicit visual feature. It is a dense, numerical summary—an "embedding"—of the image's semantic and aesthetic content.32 This vector is then saved and used as one of the primary inputs for the final multimodal fusion model, alongside the tabular data.

---

## **Part 5: Multimodal Fusion: The Core of a Modern Valuation Model**

With a tabular feature vector and a visual feature vector (or multiple, one for each image), the central technical challenge becomes how to *combine* them. This is the task of **multimodal fusion**.9 The objective is to create a single, unified representation that captures information from all modalities before feeding it to the final regression head for a price prediction. The literature on multimodal fusion provides a clear evolutionary path, from simple baselines to highly complex, state-of-the-art architectures.

### **Section 5.1: Baseline Architectures: Early, Late, and Intermediate Fusion**

The research generally identifies three main families of fusion strategies 45:

* **Late Fusion:** This is the simplest approach. Two (or more) completely independent models are trained: (1) a tabular model (e.g., XGBoost) is trained on tabular data to predict a price, and (2) a visual model (e.g., a CNN) is trained on images to predict a price. The final prediction is a simple ensemble, such as a weighted average of their individual outputs.47 This method is easy to implement but is competitively weak, as it completely misses all *cross-modal interactions* (i.e., how the tabular data should influence the interpretation of the image data, and vice-versa).  
* **Early Fusion:** This involves concatenating raw data (e.g., flattened pixel arrays and tabular numbers) at the input layer. This approach is generally ineffective for high-dimensional data like images and is not a viable strategy for this problem.  
* **Intermediate Fusion (Concatenation):** This is the most common and effective baseline architecture.46 It fuses the data at the *feature* level. The architecture is as follows:  
  1. The tabular data is passed through its own small neural network (e.g., a Multi-Layer Perceptron, or MLP) to create a low-dimensional *tabular embedding*.  
  2. The image data is passed through the CNN encoder (as described in Part 4\) to create a *visual embedding*.  
  3. These two embedding vectors are *concatenated* (stitched together) to form a single, larger vector (e.g., \[tabular\_vec, visual\_vec\]).10  
  4. This unified vector is then fed into a final "head" network (typically more MLP layers) that performs the regression, outputting a single price.

This intermediate concatenation architecture is powerful and has been explicitly used in studies on the Stockholm apartment market, where an MLP processed tabular data, a CNN processed images, and their outputs were "concatenated... which is then fed into a joint hidden layer".10

### **Section 5.2: State-of-the-Art Integration: Using Cross-Modal Attention to Weigh Visual and Tabular Data**

The intermediate fusion model is a robust baseline, but it has a subtle and significant flaw: the concatenation operation is *static*. By "gluing" the vectors together, the model must learn a single, fixed set of weights for the relationship between the visual and tabular features.

In reality, the importance of an image is *dynamic* and *context-dependent*. For example:

* **Context 1:** Tabular data shows renovation\_year: 2024 and area: 50 sqm. The images of the kitchen and bathroom become *extremely* important, as they validate the high-value renovation.  
* **Context 2:** Tabular data shows renovation\_year: 1980 and area: 50 sqm. The images of the kitchen and bathroom are now *less* important. The model should learn to *discount* them, as any potential buyer will assume a remodel is necessary, and should instead rely more heavily on the area and location features.

The static concatenation model struggles to learn this dynamic, context-switching logic. **Attention Mechanisms** are the architectural solution to this problem.46

A **cross-modal attention** layer 49 allows one modality to "query" the other, dynamically re-weighting the inputs. In this architecture, the tabular features (like renovation\_year: 2024\) can act as a *Query* or *Key* that tells the model to "pay more attention" to (i.e., apply a higher weight to) the *Values* coming from the visual feature vector.50

This is the foundation of the "gated" or "attention-based" fusion models described in advanced academic literature.51 Models described with names like "Multi-Head Gated Attention" 52 or "Joint Self-Attention Mechanism" 32 are explicitly designed to learn these complex, non-linear, and dynamic interactions between heterogeneous data modalities. This process far more closely mimics the 'logic' of a human appraiser, who intelligently synthesizes information, and represents the state-of-the-art in multimodal fusion.

### **Table 3: Multimodal Fusion Architectures**

| Fusion Strategy | Conceptual Mechanism | Performance | Research Examples |
| :---- | :---- | :---- | :---- |
| **Late Fusion** | Train separate $Model\_{tabular}$ and $Model\_{image}$. Final prediction is $w\_1 \\cdot Pred\_t \+ w\_2 \\cdot Pred\_i$. | **Baseline (Weak)** | Simple to implement, but misses all cross-modal interactions.47 |
| **Intermediate Fusion (Concatenation)** | Fuse at the feature level. $Embedding\_{tabular} \\rightarrow \[Concat\] \\leftarrow Embedding\_{image}$. Fused vector is fed to a final MLP regression head. | **Good (Strong Baseline)** | Captures feature-level interactions. This is the standard approach.10 |
| **Attention-Based Fusion (Gated/Cross-Modal)** | Fuse at the feature level with a dynamic weighting mechanism. Modality A (e.g., tabular) acts as a *Query* to re-weight Modality B (e.g., visual). | **State-of-the-Art** | Learns dynamic, context-dependent relationships between modalities.49 |

---

## **Part 6: Advanced Spatial Modeling: Capturing "Location, Location, Location"**

It is an axiom of real estate that the three most important features are "location, location, location." In a standard tabular model, location is typically represented by (latitude, longitude) coordinates or a categorical variable for the neighborhood (e.g., 'Södermalm'). These are notoriously weak and non-linear features, failing to capture the *reason* a location is valuable.

### **Section 6.1: From Coordinates to Context: Integrating Geospatial and Point-of-Interest (POI) Data**

A more robust baseline approach is to manually engineer features that represent a location's context. This involves incorporating "key spatial and neighborhood features".9 This is typically achieved by integrating **Point-of-Interest (POI)** data.

This process involves calculating and adding new features to the tabular dataset, such as:

* Distance to the nearest T-bana (subway) station.  
* Number of highly-ranked schools within a 1-kilometer radius.  
* Proximity to major parks, shopping centers, or water.9

This POI-based feature engineering provides a much richer, more "hedonic" representation of the location than simple coordinates.

### **Section 6.2: Modeling Neighborhoods as Graphs: An Introduction to GNNs for Real Estate Valuation**

The POI-list approach, while an improvement, is still a simplified, linear view of a neighborhood. The most advanced academic research treats the entire urban environment as a single, interconnected **graph**.51

In this "graph-of-peers" model:

* **Nodes:** Properties themselves are *nodes* in the graph. POIs (schools, stations) are also nodes of a different type.51  
* **Edges:** Edges connect these nodes, representing relationships. An edge might connect two properties that are "in the same neighborhood" or "within 500 meters," or connect a property node to a POI node, weighted by travel time.54

A **Graph Neural Network (GNN)** is a deep learning architecture specifically designed to learn from such graph-structured data.51 A GNN works by "message passing," where each node aggregates information from its immediate neighbors.51 In the first layer, a property node learns about itself. In the second layer, it receives "messages" from its direct neighbors (e.g., nearby properties and POIs). In the third layer, it receives messages from its neighbors' neighbors. This process allows the GNN to learn complex, emergent properties of a location that are not reducible to simple distance calculations.51

A specific method from the literature, **Geo-Spatial Network Embedding (GSNE)**, exemplifies this.54 GSNE explicitly builds a multipartite graph of houses and various POIs. It then uses a GNN to learn a dense *location embedding vector* for each property.54 This vector is a powerful, low-dimensional summary that captures the property's complete geospatial context—e.g., "this is a quiet residential street, connected to a good school, but far from nightlife."

This GNN-produced location\_embedding then becomes the *third* major input modality (alongside the tabular\_embedding and the visual\_embedding) to be fed into the multimodal fusion model described in Part 5\. Advanced GNN architectures even employ "transformer graph convolutions" to improve the message-passing mechanism, further boosting performance.51 This GNN-based approach is the current state-of-the-art for modeling location.

---

## **Part 7: Critical Risks and Data Integrity: The "Advert" Is Not Ground Truth**

A machine learning model is only as good as its data. A critical, non-obvious risk in this project is that the input images are *not* "ground truth." They are *marketing artifacts* created to present the property in the best possible light. A model that naively trusts this data will be fundamentally flawed, as it will be trained on systematically biased and, in some cases, entirely false information.

### **Section 7.1: Photographic Biases: Mitigating Lens Distortion from Wide-Angle Photography**

Real estate photographers overwhelmingly use wide-angle lenses.57 The purpose is to make small rooms (e.g., in a Stockholm apartment) appear more spacious than they are.

These lenses, however, introduce a significant geometric warping known as **barrel distortion**.58 This distortion manifests as an effect where straight lines, such as walls, doorways, and floorboards, appear to curve and stretch, especially near the edges of the frame.59

A CNN, trained on thousands of these images, will not learn that this is a photographic artifact. It will learn that "stretched corners" and "curved walls" are *positive visual features* associated with higher-priced (i.e., professionally photographed) listings. This is a classic **spurious correlation**.60 The model is not learning the *property's* quality; it is learning to reward the *photographer's* choice of lens.

The solution is a mandatory pre-processing step: **geometric distortion correction**.62 Before any image is fed to the feature-extracting CNN, it must be "un-warped" using computer vision techniques.59 This can be accomplished using standard libraries like OpenCV, which contain functions (e.g., cv2.undistort) to estimate and reverse the lens distortion parameters, transforming the image to a rectilinear projection (where straight lines are straight).64 This ensures the CNN learns from the *true* geometry of the room, not the distorted artifact.

### **Section 7.2: Deception in the Data: Identifying AI-Generated Virtual Staging and Digital Manipulation**

A more recent and severe threat to data integrity is the use of Generative AI for "virtual staging".66 This practice is rapidly moving beyond simply adding digital furniture to an empty room. Modern tools can *digitally remove walls* to create a fake "open-plan" concept, *change flooring materials*, *insert high-end appliances that do not exist*, or even *generate entire rooms*.66

This practice, as noted by legal experts and consumer advocates, "blurs the line between presentation and deception".66 Frustrated buyers who visit a property in person have described the experience as a "total catfish," finding the home looks nothing like the advertised photos.66

For a machine learning model, this is a form of *data poisoning*. The model will be trained on falsified data. It will learn, for example, that a dilapidated room with 1980s wallpaper is a "beautifully furnished modern space." This will cause the model to systematically over-predict the value of low-quality properties that have been digitally enhanced.

A production-grade system cannot trust its inputs. Therefore, it must include a **"Data Integrity Filter"**—a "model-before-the-model" to act as a gatekeeper. This filter must be an **Image Forensics** tool trained to detect two types of manipulation:

1. **AI-Generated Content Detection:** The filter must include a classifier trained to identify images produced by generative models (like Midjourney, DALL-E, etc.).69 Research in this area is active, using models like SE-ResNet-50 70 trained on large-scale synthetic image datasets 71 to distinguish real from "fake."  
2. **Image Splicing/Manipulation Detection:** The filter must also detect traditional "photoshopping" (e.g., digitally adding a fireplace). These forensic techniques analyze the image for inconsistencies in lighting, shadows, noise patterns, and textures that arise when parts of different images are "spliced" together.73

Any image flagged by this forensic filter must be handled. It could be discarded, but a more sophisticated approach is to pass it to the main valuation model with a new binary feature: is\_staged \= 1\. This allows the advanced attention-based fusion model (from Part 5.2) to *learn* to *distrust* (i.e., down-weight) the visual features for that specific property and rely more heavily on the tabular and spatial data.

---

## **Part 8: Synthesis and Strategic Recommendations for Project Development**

This final section synthesizes all preceding analyses into a single, cohesive, state-of-the-art architecture that addresses the project's core objectives while mitigating its most significant risks.

### **Section 8.1: Proposed "Trimodal Gated-Attention" Architecture**

This proposed architecture integrates the best-practice solutions identified in the research. It consists of a data-cleaning pre-processing pipeline, three parallel feature-extraction "encoders," a sophisticated fusion "brain," and a final regression "head."

1. **Data Integrity Pipeline (Pre-Processing):**  
   * *Input:* A raw image URL from the scraper.  
   * *Step 1 (Forensics):* The image is fed into the **AI Staging and Splicing Detector** model.70 This model outputs a flag: is\_staged (binary).  
   * *Step 2 (Correction):* If is\_staged \== 0, the image is processed by the **Geometric Lens Distortion Correction** algorithm (e.g., OpenCV-based).59 If is\_staged \== 1, this step may be skipped, as the geometry is already artificial.  
   * *Output:* A "clean" image (if possible) and the is\_staged flag.  
2. **Trimodal Feature Encoders (Representation Learning):**  
   * **Encoder T (Tabular):** A Multi-Layer Perceptron (MLP) processes the complete tabular vector. This vector includes all standard features (size, rooms, age, fees) *plus* the is\_staged flag from the integrity pipeline.  
     * *Output:* A low-dimensional tabular\_embedding.  
   * **Encoder V (Visual):** A pre-trained, frozen CNN (e.g., ResNet-50 43) processes the *corrected* images. If there are multiple images (kitchen, bath, etc.), their embeddings can be averaged or passed through an attention layer to create a single visual\_embedding.  
     * *Output:* A high-dimensional visual\_embedding.  
   * **Encoder S (Spatial):** A pre-trained Graph Neural Network (e.g., based on GSNE 54) processes the property's position within the pre-computed city-wide graph of properties and POIs.  
     * *Output:* A dense spatial\_embedding.  
3. **Multimodal Fusion (The "Brain"):**  
   * *Mechanism:* A Gated 52 or Cross-Modal Attention 49 module.  
   * *Function:* This module takes the three embedding vectors (tabular\_embedding, visual\_embedding, spatial\_embedding) as input. It will *learn* the optimal, *dynamic* weights for combining them on a per-sample basis. Critically, it will learn to use the is\_staged information within the tabular\_embedding to significantly *down-weight* the visual\_embedding for properties with flagged images, forcing the model to rely on the more trustworthy spatial and tabular data.  
4. **Regression Head (Prediction):**  
   * The final, weighted, fused vector, which now represents a holistic understanding of the property, is passed through a small MLP.  
   * *Output:* A single, continuous value: the predicted **'slutpris'**.

### **Section 8.2: Concluding Remarks and Future Research**

This report has detailed a comprehensive, research-backed methodology for using property images to predict prices in the Swedish real estate market. The analysis confirms the task as a multimodal supervised regression problem, for which the primary challenges are data acquisition, feature representation, and robust fusion.

Two considerations are paramount for project success. First is the non-negotiable requirement to solve the **'slutpris' data acquisition problem**.22 Any model trained on listing prices will fail. A persistent, two-stage scraping infrastructure is a prerequisite.21 Second is the **data integrity problem**.66 A model that trusts marketing images is vulnerable to data poisoning by lens distortion and AI-powered virtual staging. A data forensics pre-processing pipeline is essential for building a reliable and trustworthy valuation tool.59

Future research could extend this "trimodal" (tabular, visual, spatial) framework to a "quad-modal" one by incorporating the **listing description text**.9 This text data can be processed using NLP models (e.g., SBERT 9) to create a text\_embedding, providing a fourth stream of information for the fusion module. Furthermore, a production system would need to model **temporal and macroeconomic dynamics**, such as market-level price changes over time or the impact of interest rate shifts, which are known to be significant drivers of value.76

#### **Works cited**

1. Supervised Machine Learning \- GeeksforGeeks, accessed on November 16, 2025, [https://www.geeksforgeeks.org/machine-learning/supervised-machine-learning/](https://www.geeksforgeeks.org/machine-learning/supervised-machine-learning/)  
2. Machine Learning Project: Price Prediction Using Regression Models \- Medium, accessed on November 16, 2025, [https://medium.com/aiforwriters/machine-learning-project-price-prediction-using-regression-models-390ee20601bb](https://medium.com/aiforwriters/machine-learning-project-price-prediction-using-regression-models-390ee20601bb)  
3. Stock Market Prediction Using Machine Learning and Deep Learning Techniques: A Review, accessed on November 16, 2025, [https://www.mdpi.com/2673-9909/5/3/76](https://www.mdpi.com/2673-9909/5/3/76)  
4. Stock Market Prediction using Supervised Machine Learning Techniques: An Overview, accessed on November 16, 2025, [https://ieeexplore.ieee.org/document/9411609/](https://ieeexplore.ieee.org/document/9411609/)  
5. Identifying Real Estate Opportunities Using Machine Learning \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2076-3417/8/11/2321](https://www.mdpi.com/2076-3417/8/11/2321)  
6. Predicting Real Estate Prices Using Machine Learning in Bosnia and Herzegovina \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2306-5729/10/9/135](https://www.mdpi.com/2306-5729/10/9/135)  
7. \[2402.04082\] An Optimal House Price Prediction Algorithm: XGBoost \- arXiv, accessed on November 16, 2025, [https://arxiv.org/abs/2402.04082](https://arxiv.org/abs/2402.04082)  
8. Assessing AI Techniques for Precision in Property Valuation: A Systematic Review of the Four Valuation Methods \- Purdue e-Pubs, accessed on November 16, 2025, [https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=1790\&context=cib-conferences](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=1790&context=cib-conferences)  
9. A Multi-Modal Deep Learning Based Approach for House Price Prediction \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2409.05335v1](https://arxiv.org/html/2409.05335v1)  
10. Estimating Real Estate Selling Prices using Multimodal Neural Networks \- DiVA portal, accessed on November 16, 2025, [https://www.diva-portal.org/smash/get/diva2:1859980/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1859980/FULLTEXT01.pdf)  
11. Multimodal Machine Learning for Real Estate Appraisal: A Comprehensive Survey \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2503.22119v1](https://arxiv.org/html/2503.22119v1)  
12. arXiv:2503.22119v1 \[cs.LG\] 28 Mar 2025, accessed on November 16, 2025, [https://arxiv.org/pdf/2503.22119](https://arxiv.org/pdf/2503.22119)  
13. Austin Home Price Prediction for Multimodal Basics \- Kaggle, accessed on November 16, 2025, [https://www.kaggle.com/code/dschettler8845/austin-home-price-prediction-for-multimodal-basics](https://www.kaggle.com/code/dschettler8845/austin-home-price-prediction-for-multimodal-basics)  
14. Stock Price Prediction Website Using Linear Regression \- A Machine Learning Algorithm \- ITM Web of Conferences, accessed on November 16, 2025, [https://www.itm-conferences.org/articles/itmconf/pdf/2023/06/itmconf\_icdsac2023\_05016.pdf](https://www.itm-conferences.org/articles/itmconf/pdf/2023/06/itmconf_icdsac2023_05016.pdf)  
15. House price prediction with Convolutional Neural Network (CNN) \- WJAETS, accessed on November 16, 2025, [https://wjaets.com/sites/default/files/WJAETS-2023-0048.pdf](https://wjaets.com/sites/default/files/WJAETS-2023-0048.pdf)  
16. HOUSE PRICE PREDICTION USING DEEP LEARNING AND COMPUTER VISION TECHNIQUES \- mecsj, accessed on November 16, 2025, [https://www.mecsj.com/ar/uplode/images/photo/8e.pdf](https://www.mecsj.com/ar/uplode/images/photo/8e.pdf)  
17. Demystifying the Swedish Housing Market | by Eski's data stories \- Medium, accessed on November 16, 2025, [https://alexeskinasy.medium.com/beating-the-swedish-housing-market-with-the-booli-web-data-connector-for-tableau-3ece36a81453](https://alexeskinasy.medium.com/beating-the-swedish-housing-market-with-the-booli-web-data-connector-for-tableau-3ece36a81453)  
18. Hemnet vs Booli : r/TillSverige \- Reddit, accessed on November 16, 2025, [https://www.reddit.com/r/TillSverige/comments/1ei3bfs/hemnet\_vs\_booli/](https://www.reddit.com/r/TillSverige/comments/1ei3bfs/hemnet_vs_booli/)  
19. Booli.se Scraper \- Swedish Real Estate Extractor \- Apify, accessed on November 16, 2025, [https://apify.com/lexis-solutions/booli-se-scraper](https://apify.com/lexis-solutions/booli-se-scraper)  
20. Hemnet.se Scraper: Sweden Properties Swedish Real Estate \- Apify, accessed on November 16, 2025, [https://apify.com/lexis-solutions/hemnet-se-scraper](https://apify.com/lexis-solutions/hemnet-se-scraper)  
21. Booli Data Scraper | ScrapeIt, accessed on November 16, 2025, [https://www.scrapeit.io/real-estate-scrapers/booli](https://www.scrapeit.io/real-estate-scrapers/booli)  
22. Dan-Irl/House-Price-Prediction: Prediction of house prices ... \- GitHub, accessed on November 16, 2025, [https://github.com/Dan-Irl/House-Price-Prediction](https://github.com/Dan-Irl/House-Price-Prediction)  
23. Machine Learning for Housing in Sweden | Medium, accessed on November 16, 2025, [https://medium.com/@siddheshraw/machine-learning-for-housing-in-sweden-86456733488d](https://medium.com/@siddheshraw/machine-learning-for-housing-in-sweden-86456733488d)  
24. Empirical studies of auctions of non‐distressed residential real estate \- DiVA portal, accessed on November 16, 2025, [https://www.diva-portal.org/smash/get/diva2:1293737/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1293737/FULLTEXT01.pdf)  
25. Housing Markets and Mortgage Finance \- DiVA portal, accessed on November 16, 2025, [https://www.diva-portal.org/smash/get/diva2:1115245/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1115245/FULLTEXT01.pdf)  
26. An analysis of auction strategies in apartment sales | Request PDF \- ResearchGate, accessed on November 16, 2025, [https://www.researchgate.net/publication/326634321\_An\_analysis\_of\_auction\_strategies\_in\_apartment\_sales](https://www.researchgate.net/publication/326634321_An_analysis_of_auction_strategies_in_apartment_sales)  
27. Brokers' list price setting in an auction context | International Journal of Housing Markets and Analysis | Emerald Publishing, accessed on November 16, 2025, [https://www.emerald.com/ijhma/article/14/3/481/120469/Brokers-list-price-setting-in-an-auction-context](https://www.emerald.com/ijhma/article/14/3/481/120469/Brokers-list-price-setting-in-an-auction-context)  
28. Using AI APIs to Automate Real Estate Image Analysis and Property Listings \- Medium, accessed on November 16, 2025, [https://medium.com/@API4AI/using-ai-apis-to-automate-real-estate-image-analysis-and-property-listings-52644db21d1d](https://medium.com/@API4AI/using-ai-apis-to-automate-real-estate-image-analysis-and-property-listings-52644db21d1d)  
29. AI for Real Estate: Image-Based Property Valuation \- Plotzy, accessed on November 16, 2025, [https://plotzy.ai/blog/ai-for-real-estate-image-based-property-valuation/](https://plotzy.ai/blog/ai-for-real-estate-image-based-property-valuation/)  
30. Augmented Gallery with Property Details Makes Searching for the Perfect Home Easier, accessed on November 16, 2025, [https://techblog.realtor.com/augmented-gallery-with-property-details-makes-searching-for-the-perfect-home-easier/](https://techblog.realtor.com/augmented-gallery-with-property-details-makes-searching-for-the-perfect-home-easier/)  
31. Inside Realtor.com's AI-Powered Image Tagging Service \- Built In Austin, accessed on November 16, 2025, [https://www.builtinaustin.com/articles/inside-realtorcoms-ai-powered-image-tagging-service](https://www.builtinaustin.com/articles/inside-realtorcoms-ai-powered-image-tagging-service)  
32. Australia's Capital University Real-estate Prediction & Investment by ..., accessed on November 16, 2025, [https://researchprofiles.canberra.edu.au/files/102530699/Yun\_Zhao.pdf](https://researchprofiles.canberra.edu.au/files/102530699/Yun_Zhao.pdf)  
33. The Impact of Condition Prediction using Computer Vision on Real Estate Pricing Models \- CentAUR, accessed on November 16, 2025, [https://centaur.reading.ac.uk/125424/1/Paper\_3\_\_\_Hedonic\_Real\_Estate\_Pricing\_\_\_Deep\_Learning\_and\_House\_Front\_Images%20%281%29.pdf](https://centaur.reading.ac.uk/125424/1/Paper_3___Hedonic_Real_Estate_Pricing___Deep_Learning_and_House_Front_Images%20%281%29.pdf)  
34. Computer Vision and Real Estate: Do Looks Matter and Do Incentives Determine Looks, accessed on November 16, 2025, [https://www.nber.org/system/files/working\_papers/w25174/w25174.pdf](https://www.nber.org/system/files/working_papers/w25174/w25174.pdf)  
35. What Image Features Boost Housing Market Predictions? | IEEE Journals & Magazine, accessed on November 16, 2025, [https://ieeexplore.ieee.org/document/8960418/](https://ieeexplore.ieee.org/document/8960418/)  
36. From platforms to price: the impact of condition prediction using computer vision on real estate pricing models \- Emerald Publishing, accessed on November 16, 2025, [https://www.emerald.com/jerer/article/doi/10.1108/JERER-03-2024-0013/1277206/From-platforms-to-price-the-impact-of-condition](https://www.emerald.com/jerer/article/doi/10.1108/JERER-03-2024-0013/1277206/From-platforms-to-price-the-impact-of-condition)  
37. Real estate valuation with multi-source image fusion and enhanced ..., accessed on November 16, 2025, [https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0321951](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0321951)  
38. (PDF) Predicting Housing Prices Using Advanced Analytics: A Study on Key Property Features and Market Dynamics \- ResearchGate, accessed on November 16, 2025, [https://www.researchgate.net/publication/390475372\_Predicting\_Housing\_Prices\_Using\_Advanced\_Analytics\_A\_Study\_on\_Key\_Property\_Features\_and\_Market\_Dynamics](https://www.researchgate.net/publication/390475372_Predicting_Housing_Prices_Using_Advanced_Analytics_A_Study_on_Key_Property_Features_and_Market_Dynamics)  
39. The Application of ResNet-34 Model Integrating Transfer Learning in the Recognition and Classification of Overseas Chinese Frescoes \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2079-9292/12/17/3677](https://www.mdpi.com/2079-9292/12/17/3677)  
40. Deep Learning for Image Classification on Very Small Datasets Using Transfer \- Iowa State University Digital Repository, accessed on November 16, 2025, [https://dr.lib.iastate.edu/server/api/core/bitstreams/e72a8f4f-adb3-48d3-9831-0bc95e7e1edb/content](https://dr.lib.iastate.edu/server/api/core/bitstreams/e72a8f4f-adb3-48d3-9831-0bc95e7e1edb/content)  
41. Evaluating Transfer Learning in Deep Learning Models for Classification on a Custom Wildlife Dataset: Can YOLOv8 Surpass Other Architectures? \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2408.00002v1](https://arxiv.org/html/2408.00002v1)  
42. Evaluation of transfer ensemble learning-based convolutional neural network models for the identification of chronic gingivitis from oral photographs \- PMC, accessed on November 16, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11256452/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11256452/)  
43. Effect of transfer learning on the performance of VGGNet-16 and ResNet-50 for the classification of organic and residual waste \- Frontiers, accessed on November 16, 2025, [https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.1043843/full](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.1043843/full)  
44. From Traditional House Price Appraisal to Computer Vision-Based: A Survey | Request PDF, accessed on November 16, 2025, [https://www.researchgate.net/publication/349772861\_From\_Traditional\_House\_Price\_Appraisal\_to\_Computer\_Vision-Based\_A\_Survey](https://www.researchgate.net/publication/349772861_From_Traditional_House_Price_Appraisal_to_Computer_Vision-Based_A_Survey)  
45. Effective Techniques for Multimodal Data Fusion: A Comparative Analysis \- PMC, accessed on November 16, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10007548/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007548/)  
46. Fusion Model Guide — fusilli documentation \- Read the Docs, accessed on November 16, 2025, [https://fusilli.readthedocs.io/en/latest/fusion\_model\_explanations.html](https://fusilli.readthedocs.io/en/latest/fusion_model_explanations.html)  
47. Multi-Modal Deep Learning: Combining Computer Vision and NLP for Enhanced AI | by Mubarak Khan | Medium, accessed on November 16, 2025, [https://medium.com/@mubarak.k1919/multi-modal-deep-learning-combining-computer-vision-and-nlp-for-enhanced-ai-27ce6dda3a86](https://medium.com/@mubarak.k1919/multi-modal-deep-learning-combining-computer-vision-and-nlp-for-enhanced-ai-27ce6dda3a86)  
48. Cross attention for Text and Image Multimodal data fusion \- Stanford University, accessed on November 16, 2025, [https://web.stanford.edu/class/cs224n/final-reports/256711050.pdf](https://web.stanford.edu/class/cs224n/final-reports/256711050.pdf)  
49. A Cross-Modal Attention-Driven Multi-Sensor Fusion Method for Semantic Segmentation of Point Clouds \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/1424-8220/25/8/2474](https://www.mdpi.com/1424-8220/25/8/2474)  
50. CMAF-Net: a cross-modal attention fusion-based deep neural network for incomplete multi-modal brain tumor segmentation \- NIH, accessed on November 16, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11250309/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11250309/)  
51. arxiv.org, accessed on November 16, 2025, [https://arxiv.org/html/2405.06553v1](https://arxiv.org/html/2405.06553v1)  
52. Enhancing house price forecasting with hybrid data driven feature extraction model, accessed on November 16, 2025, [https://www.tandfonline.com/doi/full/10.1080/01605682.2025.2513449?af=R](https://www.tandfonline.com/doi/full/10.1080/01605682.2025.2513449?af=R)  
53. Boosting House Price Estimations with Multi-Head Gated Attention \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2405.07456v1](https://arxiv.org/html/2405.07456v1)  
54. (PDF) Boosting House Price Predictions using Geo-Spatial Network ..., accessed on November 16, 2025, [https://arxiv.org/abs/2009.00254](https://arxiv.org/abs/2009.00254)  
55. Scalable Property Valuation Models via Graph-based Deep Learning \- arXiv, accessed on November 16, 2025, [https://arxiv.org/pdf/2405.06553](https://arxiv.org/pdf/2405.06553)  
56. Using Graph Neural Networks to Predict Local Culture \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2402.17905v1](https://arxiv.org/html/2402.17905v1)  
57. A 360 DEGREE VIEW OF REALITY: CAN 360° IMAGES REDUCE “MANUFACTURED” BIAS IN PHOTOGRAPHY? | Request PDF \- ResearchGate, accessed on November 16, 2025, [https://www.researchgate.net/publication/358497243\_A\_360\_DEGREE\_VIEW\_OF\_REALITY\_CAN\_360\_IMAGES\_REDUCE\_MANUFACTURED\_BIAS\_IN\_PHOTOGRAPHY](https://www.researchgate.net/publication/358497243_A_360_DEGREE_VIEW_OF_REALITY_CAN_360_IMAGES_REDUCE_MANUFACTURED_BIAS_IN_PHOTOGRAPHY)  
58. Evaluating the Impact of Wide-Angle Lens Distortion on Learning-Based Depth Estimation \- CVF Open Access, accessed on November 16, 2025, [https://openaccess.thecvf.com/content/CVPR2021W/OmniCV/papers/Buquet\_Evaluating\_the\_Impact\_of\_Wide-Angle\_Lens\_Distortion\_on\_Learning-Based\_Depth\_CVPRW\_2021\_paper.pdf](https://openaccess.thecvf.com/content/CVPR2021W/OmniCV/papers/Buquet_Evaluating_the_Impact_of_Wide-Angle_Lens_Distortion_on_Learning-Based_Depth_CVPRW_2021_paper.pdf)  
59. Blind Geometric Distortion Correction on Images Through Deep Learning \- CVF Open Access, accessed on November 16, 2025, [https://openaccess.thecvf.com/content\_CVPR\_2019/papers/Li\_Blind\_Geometric\_Distortion\_Correction\_on\_Images\_Through\_Deep\_Learning\_CVPR\_2019\_paper.pdf](https://openaccess.thecvf.com/content_CVPR_2019/papers/Li_Blind_Geometric_Distortion_Correction_on_Images_Through_Deep_Learning_CVPR_2019_paper.pdf)  
60. Fairness and Bias Mitigation in Computer Vision: A Survey \- arXiv, accessed on November 16, 2025, [https://arxiv.org/html/2408.02464v1](https://arxiv.org/html/2408.02464v1)  
61. (PDF) Fairness and Bias Mitigation in Computer Vision: A Survey \- ResearchGate, accessed on November 16, 2025, [https://www.researchgate.net/publication/382885634\_Fairness\_and\_Bias\_Mitigation\_in\_Computer\_Vision\_A\_Survey](https://www.researchgate.net/publication/382885634_Fairness_and_Bias_Mitigation_in_Computer_Vision_A_Survey)  
62. Removing lens geometric distortion through advanced image processing \- Basler, accessed on November 16, 2025, [https://www.baslerweb.com/en/use-cases/remove-lens-distortion/](https://www.baslerweb.com/en/use-cases/remove-lens-distortion/)  
63. Wide-Angle Image Distortion Correction and Embedded Stitching System Design Based on Swin Transformer \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2076-3417/15/14/7714](https://www.mdpi.com/2076-3417/15/14/7714)  
64. How to normalize an image in OpenCV Python? \- Tutorials Point, accessed on November 16, 2025, [https://www.tutorialspoint.com/how-to-normalize-an-image-in-opencv-python](https://www.tutorialspoint.com/how-to-normalize-an-image-in-opencv-python)  
65. Camera Calibration and 3D Reconstruction \- OpenCV Documentation, accessed on November 16, 2025, [https://docs.opencv.org/4.x/d9/d0c/group\_\_calib3d.html](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)  
66. AI Images Infiltrate Real Estate Listings: What to Know \- SFL Media, accessed on November 16, 2025, [https://sfl.media/ai-images-infiltrate-real-estate-listings-what-to-know/](https://sfl.media/ai-images-infiltrate-real-estate-listings-what-to-know/)  
67. Using AI to Transform Real Estate Images | Florida Realtors, accessed on November 16, 2025, [https://www.floridarealtors.org/news-media/news-articles/2024/02/using-ai-transform-real-estate-images](https://www.floridarealtors.org/news-media/news-articles/2024/02/using-ai-transform-real-estate-images)  
68. Picture-Perfect Lies and the Productivity Truth: AI's Real World Reality Check, accessed on November 16, 2025, [https://www.getbigthink.com/post/picture-perfect-lies-and-the-productivity-truth-ai-s-real-world-reality-check](https://www.getbigthink.com/post/picture-perfect-lies-and-the-productivity-truth-ai-s-real-world-reality-check)  
69. AI image detector. Detect AI-generated media at scale \- Sightengine, accessed on November 16, 2025, [https://sightengine.com/detect-ai-generated-images](https://sightengine.com/detect-ai-generated-images)  
70. Detecting AI-Generated Images Using a Hybrid ResNet-SE Attention Model \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2076-3417/15/13/7421](https://www.mdpi.com/2076-3417/15/13/7421)  
71. (PDF) Detecting AI Generated Images Through Texture and Frequency Analysis of Patches, accessed on November 16, 2025, [https://www.researchgate.net/publication/387792397\_Detecting\_AI\_Generated\_Images\_through\_Texture\_and\_Frequency\_Analysis\_of\_Patches](https://www.researchgate.net/publication/387792397_Detecting_AI_Generated_Images_through_Texture_and_Frequency_Analysis_of_Patches)  
72. \[2502.15176\] Methods and Trends in Detecting AI-Generated Images: A Comprehensive Review \- arXiv, accessed on November 16, 2025, [https://arxiv.org/abs/2502.15176](https://arxiv.org/abs/2502.15176)  
73. How to Detect Image Tampering Using Image Forensics and AI \- Klippa, accessed on November 16, 2025, [https://www.klippa.com/en/blog/information/image-tampering-detection/](https://www.klippa.com/en/blog/information/image-tampering-detection/)  
74. Detection of Manipulations in Digital Images: A Review of Passive and Active Methods Utilizing Deep Learning \- MDPI, accessed on November 16, 2025, [https://www.mdpi.com/2076-3417/15/2/881](https://www.mdpi.com/2076-3417/15/2/881)  
75. Comprehensive analyses of image forgery detection methods from traditional to deep learning approaches: an evaluation \- NIH, accessed on November 16, 2025, [https://pmc.ncbi.nlm.nih.gov/articles/PMC9525232/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9525232/)  
76. Predicting Commercial Real Estate Prices in Sweden Using Gradient Boosting and Random Forest Models \- DiVA portal, accessed on November 16, 2025, [http://www.diva-portal.org/smash/get/diva2:1967655/FULLTEXT01.pdf](http://www.diva-portal.org/smash/get/diva2:1967655/FULLTEXT01.pdf)