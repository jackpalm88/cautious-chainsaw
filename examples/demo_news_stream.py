"""
Demo: NewsStream v1.9
Demonstrates news integration with Input Fusion
"""

import asyncio
from datetime import datetime

from src.trading_agent.input_fusion import (
    InputFusionEngine,
    NewsNormalizer,
    NewsStream,
    PriceStream,
    SentimentAnalyzer,
    SymbolRelevanceScorer,
)


async def demo_news_normalizer():
    """Demo: News normalization"""
    print("\n" + "=" * 70)
    print("1️⃣  NEWS NORMALIZER DEMO")
    print("=" * 70)

    normalizer = NewsNormalizer()

    # NewsAPI format
    raw_newsapi = {
        "title": "ECB hints at potential rate cut in Q4",
        "description": "European Central Bank officials suggest monetary policy easing amid economic slowdown",
        "source": {"name": "Reuters"},
        "url": "https://example.com/news/ecb-rate-cut",
        "publishedAt": "2025-01-15T10:30:00Z",
        "author": "John Smith",
    }

    normalized = normalizer.normalize_newsapi(raw_newsapi)

    print(f"\n📰 NEWSAPI NORMALIZATION:")
    print(f"  Title: {normalized.title}")
    print(f"  Source: {normalized.source}")
    print(f"  Published: {normalized.published_at}")
    print(f"  Major Event: {normalized.is_major_event}")
    print(f"  URL: {normalized.url}")


async def demo_symbol_relevance():
    """Demo: Symbol relevance scoring"""
    print("\n" + "=" * 70)
    print("2️⃣  SYMBOL RELEVANCE SCORING DEMO")
    print("=" * 70)

    normalizer = NewsNormalizer()
    scorer = SymbolRelevanceScorer()

    # Create test news
    test_news = [
        {
            "title": "ECB announces euro policy change",
            "description": "European Central Bank adjusts eurozone interest rates",
            "source": {"name": "Bloomberg"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
        {
            "title": "Gold prices surge on safe-haven demand",
            "description": "Precious metals rally amid geopolitical tensions",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
        {
            "title": "Tech stocks rally on AI optimism",
            "description": "Technology sector leads market gains",
            "source": {"name": "CNBC"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
    ]

    # Normalize
    normalized_news = [normalizer.normalize_newsapi(n) for n in test_news]

    # Calculate relevance for different symbols
    symbols = ["EURUSD", "XAUUSD", "BTCUSD"]

    print(f"\n📊 RELEVANCE SCORES:")
    print(f"{'News Title':<50} {'Symbol':<10} {'Score':<10}")
    print("-" * 70)

    for news in normalized_news:
        for symbol in symbols:
            relevance = scorer.calculate_relevance(news, symbol)
            if relevance > 0.3:  # Only show relevant news
                title_short = news.title[:47] + "..." if len(news.title) > 47 else news.title
                print(f"{title_short:<50} {symbol:<10} {relevance:<10.3f}")


async def demo_sentiment_analysis():
    """Demo: Sentiment analysis"""
    print("\n" + "=" * 70)
    print("3️⃣  SENTIMENT ANALYSIS DEMO")
    print("=" * 70)

    normalizer = NewsNormalizer()
    analyzer = SentimentAnalyzer(mode="rule_based")

    # Test news with different sentiments
    test_news = [
        {
            "title": "Markets surge on positive economic data",
            "description": "Strong growth and optimistic outlook boost investor confidence",
            "source": {"name": "Reuters"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
        {
            "title": "Markets plunge on recession fears",
            "description": "Economic decline and weak data trigger bearish sentiment",
            "source": {"name": "Bloomberg"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
        {
            "title": "Central bank maintains current policy",
            "description": "Officials to monitor economic conditions",
            "source": {"name": "CNBC"},
            "url": "https://example.com",
            "publishedAt": datetime.now().isoformat(),
        },
    ]

    print(f"\n💭 SENTIMENT SCORES:")
    print(f"{'News Title':<50} {'Sentiment':<12} {'Score':<8} {'Conf':<8}")
    print("-" * 78)

    for raw in test_news:
        news = normalizer.normalize_newsapi(raw)
        sentiment, confidence = analyzer.analyze(news)
        label = analyzer.get_sentiment_label(sentiment)

        title_short = news.title[:47] + "..." if len(news.title) > 47 else news.title
        print(f"{title_short:<50} {label:<12} {sentiment:>7.3f} {confidence:>7.3f}")


async def demo_news_stream():
    """Demo: NewsStream with Input Fusion"""
    print("\n" + "=" * 70)
    print("4️⃣  NEWS STREAM + INPUT FUSION DEMO")
    print("=" * 70)

    # Create streams
    symbols = ["EURUSD", "XAUUSD"]

    price_stream1 = PriceStream(symbol="EURUSD", mode="mock", update_interval_ms=500)
    price_stream2 = PriceStream(symbol="XAUUSD", mode="mock", update_interval_ms=500)
    news_stream = NewsStream(
        symbols=symbols,
        mode="mock",
        fetch_interval_s=2,  # Fetch every 2 seconds
        relevance_threshold=0.4,
    )

    # Create fusion engine
    engine = InputFusionEngine(
        buffer_capacity=1000,
    )

    # Add streams
    engine.add_stream(price_stream1)
    engine.add_stream(price_stream2)
    engine.add_stream(news_stream)

    print(f"\n🔄 Starting Input Fusion with News...")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Streams: 2 price + 1 news")
    print(f"  News Fetch Interval: 2s")

    # Start engine
    await engine.start()

    # Run for 5 seconds
    print(f"\n⏳ Collecting data for 5 seconds...")
    await asyncio.sleep(5)

    # Stop engine
    await engine.stop()

    # Get statistics
    stats = engine.get_stats()

    print(f"\n📊 FUSION STATISTICS:")
    print(f"  Total Fusions: {stats['fusion_count']}")
    print(f"  Active Streams: {stats['stream_count']}")
    print(f"  Sync Window: {stats['sync_window_ms']}ms")
    print(f"  Memory Usage: {stats['memory']['total_mb']:.2f} MB")

    # Get latest snapshot
    snapshot = engine.get_latest_snapshot()

    if snapshot:
        print(f"\n📸 LATEST FUSED SNAPSHOT:")
        print(f"  Timestamp: {snapshot.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"  Streams: {len(snapshot.data)}")

        # Show prices
        print(f"\n  💱 PRICES:")
        for stream_id, data in snapshot.data.items():
            if "price" in stream_id:
                symbol = data.get("symbol", "Unknown")
                bid = data.get("bid", 0)
                ask = data.get("ask", 0)
                spread = data.get("spread", 0)
                print(f"    {symbol:<8} Bid: {bid:.5f}  Ask: {ask:.5f}  Spread: {spread:.5f}")

        # Show news
        print(f"\n  📰 NEWS:")
        for stream_id, data in snapshot.data.items():
            if "news" in stream_id:
                title = data.get("title", "No title")
                symbols_list = data.get("symbols", [])
                relevance = data.get("relevance_score", 0)
                sentiment = data.get("sentiment_score")

                print(f"    Title: {title[:60]}...")
                print(f"    Symbols: {', '.join(symbols_list)}")
                print(f"    Relevance: {relevance:.3f}")
                if sentiment is not None:
                    print(f"    Sentiment: {sentiment:.3f}")


async def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("📰 NEWSSTREAM v1.9 DEMO")
    print("=" * 70)

    await demo_news_normalizer()
    await demo_symbol_relevance()
    await demo_sentiment_analysis()
    await demo_news_stream()

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
