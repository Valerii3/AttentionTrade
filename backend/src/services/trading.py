"""
Belief-based pricing: price_up = sigmoid(net_up / liquidity), price_down = 1 - price_up.
"""
import math

LIQUIDITY = 20.0  # scaling for sigmoid


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def prices_from_position(net_up: float, net_down: float) -> tuple[float, float]:
    # Net position: more "up" buys -> higher price_up
    net = net_up - net_down
    price_up = sigmoid(net / LIQUIDITY)
    price_down = 1.0 - price_up
    return round(price_up, 4), round(price_down, 4)
