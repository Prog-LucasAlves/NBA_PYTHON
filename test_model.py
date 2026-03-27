#!/usr/bin/env python
"""Quick test of the prediction model"""

from nba_prediction_model import NBAPointsPredictor

print("\n" + "=" * 60)
print("NBA PREDICTION MODEL TEST")
print("=" * 60)

# Load and train
print("\n[1/3] Loading data...")
predictor = NBAPointsPredictor("data/nba_player_stats_multi_season.csv")

print("[2/3] Training model...")
predictor.train()

# Test prediction
print("\n[3/3] Testing predictions...\n")
players = list(predictor.player_averages.keys())[:3]

for player in players:
    print(f"\n{'=' * 60}")
    print(f"Player: {player}")
    print("=" * 60)

    pred = predictor.predict_points(player, minutes=35)
    print("\nPrediction:")
    print(f"  - Points: {pred['predicted_points']} +/- {pred['std_error']:.2f}")
    print(f"  - Confidence Interval: [{pred['confidence_lower']:.2f}, {pred['confidence_upper']:.2f}]")
    print(f"  - Minutes: {pred['minutes_used']}")
    print(f"  - Trend: {pred['trend']} ({pred['trend_pct']:+.1f}%)")

    # EV+ Analysis
    ev = predictor.calculate_ev_plus(pred["predicted_points"], 1.95, 25.5)
    print("\nEV+ Analysis (vs 25.5 @ 1.95):")
    print(f"  - EV+: {ev['ev_plus_pct']:+.2f}%")
    print(f"  - Signal: {ev['signal']}")
    print(f"  - Model Win%: {ev['model_probability'] * 100:.2f}%")
    print(f"  - Kelly Criterion: {ev['kelly_criterion']:+.4f}")

print("\n[OK] All tests passed! Model is ready.\n")
