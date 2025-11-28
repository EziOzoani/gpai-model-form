# Enhanced Region Detection for crawl.py

## Overview
The crawl.py script has been enhanced with sophisticated region detection capabilities that automatically identify the geographical region of AI model providers based on multiple signals from the scraped content.

## Key Enhancements

### 1. Multi-Signal Region Detection
The new `detect_region_from_content()` function analyzes multiple signals to determine the provider's region:

- **Provider-specific mappings**: Known providers are mapped to their primary regions
- **Text content analysis**: Searches for region-specific keywords and patterns
- **URL domain analysis**: Checks domain extensions (.eu, .uk, .cn, etc.)
- **Regulatory mentions**: Detects references to region-specific regulations (GDPR, EU AI Act, etc.)
- **Legal entity suffixes**: Identifies company type suffixes (Inc, Ltd, GmbH, etc.)
- **Headquarters detection**: Extracts location information from headquarters mentions
- **Deployment regions**: Identifies data center and server locations
- **Multi-region presence**: Detects providers with presence in multiple regions

### 2. Supported Regions
The system now detects the following regions:
- **US**: United States
- **EU**: European Union
- **UK**: United Kingdom
- **CN**: China
- **CA**: Canada
- **JP**: Japan
- **KR**: South Korea
- **IL**: Israel
- **AU**: Australia
- **SG**: Singapore
- **IN**: India (through domain detection)

### 3. Scoring System
- Each signal contributes a weighted score to potential regions
- URL domains provide the highest weight (10 points)
- Headquarters mentions add 5 points
- Regulatory mentions add 3 points
- Entity suffixes add 2 points
- Other mentions add 1 point each

### 4. Global Provider Handling
For providers with similar scores across multiple regions:
- Detects if it's a known global provider (Google, Microsoft, Amazon, IBM)
- Defaults to their primary headquarters region (typically US)
- Logs multi-region presence for transparency

### 5. Provenance Tracking
Region detection information is now included in the provenance data:
- `region_detected`: The detected region
- `region_detection_method`: Whether it was automatic or fallback

### 6. Parser Updates
All parser functions have been updated to:
- Accept a `source_url` parameter
- Call `detect_region_from_content()` instead of hardcoding regions
- Pass the detected region to `create_model_record()`

## Usage
The region detection happens automatically when crawling sources. No changes to the main crawling logic are required.

## Testing
A test script `test_region_detection.py` is provided to verify the region detection logic with various test cases.

## Benefits
1. **Accuracy**: More accurate region identification based on actual content
2. **Flexibility**: Can detect regions for new providers without code changes
3. **Transparency**: Logs explain how regions were determined
4. **Compliance**: Better tracking for regional AI regulations
5. **Scalability**: Works with any provider, not just hardcoded ones

## Future Enhancements
Potential improvements could include:
- Machine learning-based region detection
- Integration with external geolocation APIs
- Support for more regions
- Confidence scores for region detection
- Handling of providers that operate under different entities in different regions