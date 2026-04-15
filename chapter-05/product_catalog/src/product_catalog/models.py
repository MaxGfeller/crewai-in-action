from pydantic import BaseModel


class ProductFeatures(BaseModel):
    category: str
    colors: list[str]
    materials: list[str]
    visible_text: list[str]
    estimated_dimensions: str
    condition: str
    notable_features: list[str]
    brand_indicators: list[str]


class ProductListing(BaseModel):
    title: str
    description: str
    bullet_points: list[str]
    seo_keywords: list[str]
    suggested_category: str


class SimilarProduct(BaseModel):
    title: str
    similarity_score: float
    price: float
    key_differences: list[str]


class CatalogFindings(BaseModel):
    similar_products: list[SimilarProduct]
    suggested_price_range: str
