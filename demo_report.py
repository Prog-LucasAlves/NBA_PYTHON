#!/usr/bin/env python
"""
NBA Betting Predictor Pro - Demonstration Script
Shows various players and EV+ analysis scenarios
"""

from nba_prediction_model import NBAPointsPredictor

print("\n" + "=" * 80)
print(" " * 10 + "NBA SPORTS BETTING PREDICTOR PRO")
print(" " * 20 + "Demonstration & Analysis Report")
print("=" * 80)

# Load and train model
print("\n[Loading Model...]")
predictor = NBAPointsPredictor("data/nba_player_stats_multi_season.csv")
predictor.train()

print("\n[OK] Model Ready!")
if predictor.df is not None:
    print(f"  - Dataset: {len(predictor.df)} records, {len(predictor.player_averages)} players")
    print(f"  - Accuracy (R2): {predictor.model_stats['r2']:.4f}")
    print(f"  - Prediction Error (MAE): {predictor.model_stats['mae']:.2f} points")
    print(f"  - Confidence Interval: +/- {predictor.model_stats['std_error']:.2f} points")

# Demonstration scenarios
print("\n" + "=" * 80)
print("SCENARIO 1: STRONG VALUE BET (O/U 20.5 @ 1.95)")
print("=" * 80)

# Find player with low line prediction
test_player = "Austin Reaves"
pred = predictor.predict_points(test_player, minutes=32)
ev = predictor.calculate_ev_plus(pred["predicted_points"], 1.95, 20.5)

print(f"\nPlayer: {test_player}")
print(f"Predicted Points: {pred['predicted_points']:.2f} +/- {pred['std_error']:.2f}")
print(f"Trend: {pred['trend']} ({pred['trend_pct']:+.1f}%)")
print("\nBetting Setup:")
print("  Market Line: 20.5")
print(f"  Decimal Odds: {ev['market_odds']}")
print("  Expected Minutes: 32")
print("\nEV+ Analysis:")
print(f"  Model Win% (Over 20.5): {ev['model_probability'] * 100:.2f}%")
print(f"  Expected Value: {ev['ev_plus_pct']:+.2f}%")
print(f"  Signal: {ev['signal']}")
print(f"  Recommendation: {ev['recommendation']}")
print(f"  Kelly Criterion: {ev['kelly_criterion']:.4f} ({ev['kelly_criterion'] * 100:.2f}%)")

print("\n" + "=" * 80)
print("SCENARIO 2: FAIR VALUE BET (O/U 28.5 @ 1.95)")
print("=" * 80)

test_player2 = "Jayson Tatum"
if test_player2 in predictor.player_averages:
    pred2 = predictor.predict_points(test_player2, minutes=36)
    ev2 = predictor.calculate_ev_plus(pred2["predicted_points"], 1.95, 28.5)

    print(f"\nPlayer: {test_player2}")
    print(f"Predicted Points: {pred2['predicted_points']:.2f} +/- {pred2['std_error']:.2f}")
    print(f"Trend: {pred2['trend']} ({pred2['trend_pct']:+.1f}%)")
    print("\nBetting Setup:")
    print("  Market Line: 28.5")
    print(f"  Decimal Odds: {ev2['market_odds']}")
    print("  Expected Minutes: 36")
    print("\nEV+ Analysis:")
    print(f"  Model Win% (Over 28.5): {ev2['model_probability'] * 100:.2f}%")
    print(f"  Expected Value: {ev2['ev_plus_pct']:+.2f}%")
    print(f"  Signal: {ev2['signal']}")
    print(f"  Recommendation: {ev2['recommendation']}")
    print(f"  Kelly Criterion: {ev2['kelly_criterion']:.4f} ({ev2['kelly_criterion'] * 100:.2f}%)")
else:
    print(f"\n[WARNING] Player '{test_player2}' not found. Trying alternative...")
    players = list(predictor.player_averages.keys())
    test_player2 = players[100]
    pred2 = predictor.predict_points(test_player2, minutes=30)
    ev2 = predictor.calculate_ev_plus(pred2["predicted_points"], 1.95, 24.5)

    print(f"\nUsing: {test_player2}")
    print(f"Predicted Points: {pred2['predicted_points']:.2f} +/- {pred2['std_error']:.2f}")
    print(f"  Signal: {ev2['signal']}")
    print(f"  Recommendation: {ev2['recommendation']}")

print("\n" + "=" * 80)
print("SCENARIO 3: TOP SCORERS ANALYSIS (O/U 28.5 @ 1.95)")
print("=" * 80)

# Find top 5 average scorers
top_scorers = sorted(predictor.player_averages.items(), key=lambda x: x[1]["avg_pts"], reverse=True)[:5]

print("\nTop 5 Average Scorers:")
print("-" * 80)
print(f"{'Player':<20} {'Avg PPG':<12} {'Pred 28.5@1.95':<15} {'EV+':<10} {'Signal':<15}")
print("-" * 80)

for player, stats in top_scorers:
    pred = predictor.predict_points(player, minutes=35)
    ev = predictor.calculate_ev_plus(pred["predicted_points"], 1.95, 28.5)

    print(f"{player:<20} {stats['avg_pts']:<12.1f} {pred['predicted_points']:<15.2f} {ev['ev_plus_pct']:<10.2f}% {ev['signal']:<15}")

print("\n" + "=" * 80)
print("KEY METRICS SUMMARY")
print("=" * 80)

print(f"""
[OK] Model Performance:
  - R2 Score: {predictor.model_stats["r2"]:.4f} (Explains {predictor.model_stats["r2"] * 100:.2f}% of variance)
  - RMSE: {predictor.model_stats["rmse"]:.2f} points (root mean squared error)
  - MAE: {predictor.model_stats["mae"]:.2f} points (typical prediction error)
  - Std Dev: {predictor.model_stats["std_error"]:.2f} points (confidence +/- 1 sigma)

[OK] Top 3 Most Important Features:
""")

feature_importance = sorted(predictor.model_stats["feature_importance"].items(), key=lambda x: x[1], reverse=True)[:3]

for i, (feature, importance) in enumerate(feature_importance, 1):
    print(f"  {i}. {feature}: {importance:.4f}")

if predictor.df is not None:
    print(f"""
[OK] Dataset Coverage:
  - Total Records: {len(predictor.df)}
  - Unique Players: {len(predictor.player_averages)}
  - Seasons: {sorted(predictor.df["SEASON"].unique())}
  - Avg Games per Season: {predictor.df.groupby("SEASON")["PLAYER_NAME"].nunique().mean():.0f}

[OK] How to Use:
  1. Run: streamlit run betting_app.py
  2. Select a player from the sidebar
  3. Enter market line and odds
  4. Review EV+ analysis
  5. Use Kelly Criterion for bet sizing

[WARNING] Remember: All predictions are statistical estimates, not guarantees!
   Always practice responsible gambling.
""")

print("\n" + "=" * 80)
print(" " * 20 + "Report Generated Successfully!")
print("=" * 80 + "\n")
