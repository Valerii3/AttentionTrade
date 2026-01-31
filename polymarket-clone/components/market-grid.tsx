"use client";

import { MarketCard, SportsMarketCard, type Market } from "./market-card";

const markets: Market[] = [
  {
    id: "1",
    title: "How long will the Government Shutdown last?",
    type: "binary",
    image: "/markets/gov.jpg",
    options: [
      { name: "2+ days", odds: 100 },
      { name: "3+ days", odds: 99 },
    ],
    volume: "$5m",
  },
  {
    id: "2",
    title: "Alexander Volkanovski vs Diego Lopes",
    type: "versus",
    options: [
      { name: "Alexander Volkanovski", odds: 59, image: "/markets/fighter1.jpg" },
      { name: "Diego Lopes", odds: 42, image: "/markets/fighter2.jpg" },
    ],
    volume: "$547k",
    category: "UFC",
    eventTime: "Tomorrow 3:00 AM",
  },
  {
    id: "3",
    title: "Grammys: Song of the Year Winner",
    type: "multi",
    image: "/markets/grammys.jpg",
    options: [
      { name: "Golden [From \"KPop...", odds: 79 },
      { name: "luther - Kendrick Lama...", odds: 12 },
    ],
    volume: "$1m",
  },
  {
    id: "4",
    title: "Seahawks vs Patriots",
    type: "versus",
    options: [
      { name: "Seahawks", odds: 69, image: "/markets/seahawks.jpg" },
      { name: "Patriots", odds: 32, image: "/markets/patriots.jpg" },
    ],
    volume: "$6m",
    category: "NFL",
    eventTime: "Feb 09, 12:30 AM",
  },
  {
    id: "5",
    title: "3DMAX vs FaZe",
    type: "versus",
    options: [
      { name: "3DMAX", odds: 64, image: "/markets/3dmax.jpg" },
      { name: "FaZe", odds: 37, image: "/markets/faze.jpg" },
    ],
    volume: "$506k",
    category: "COUNTER STRIKE",
    isLive: true,
    gameInfo: "Game 2 · Best of 3",
  },
  {
    id: "6",
    title: "Vitality vs BC.Game Esports",
    type: "versus",
    options: [
      { name: "Vitality", odds: 81, image: "/markets/vitality.jpg" },
      { name: "BC.Game Esports", odds: 20, image: "/markets/bcgame.jpg" },
    ],
    volume: "$412k",
    category: "COUNTER STRIKE",
    isLive: true,
    gameInfo: "Game 1 · Best of 3",
  },
  {
    id: "7",
    title: "Liverpool vs Newcastle",
    type: "versus",
    options: [
      { name: "Liverpool", odds: 59, image: "/markets/liverpool.jpg" },
      { name: "Newcastle", odds: 19, image: "/markets/newcastle.jpg" },
    ],
    volume: "$3m",
    category: "EPL",
    eventTime: "9:00 PM",
  },
  {
    id: "8",
    title: "Cloud9 vs LYON",
    type: "versus",
    options: [
      { name: "Cloud9", odds: 68, image: "/markets/cloud9.jpg" },
      { name: "LYON", odds: 33, image: "/markets/lyon.jpg" },
    ],
    volume: "$756k",
    category: "LEAGUE OF LEGENDS",
    eventTime: "10:00 PM",
  },
  {
    id: "9",
    title: "Pelicans vs 76ers",
    type: "versus",
    options: [
      { name: "Pelicans", odds: 31, image: "/markets/pelicans.jpg" },
      { name: "76ers", odds: 70, image: "/markets/76ers.jpg" },
    ],
    volume: "$2m",
    category: "NBA",
    eventTime: "Tomorrow 1:30 AM",
  },
  {
    id: "10",
    title: "Mavericks vs Rockets",
    type: "versus",
    options: [
      { name: "Mavericks", odds: 22, image: "/markets/mavs.jpg" },
      { name: "Rockets", odds: 79, image: "/markets/rockets.jpg" },
    ],
    volume: "$2m",
    category: "NBA",
    eventTime: "Tomorrow 2:30 AM",
  },
  {
    id: "11",
    title: "US strikes Iran by...?",
    type: "binary",
    image: "/markets/iran.jpg",
    options: [
      { name: "February 6", odds: 19 },
      { name: "February 13", odds: 36 },
    ],
    volume: "$139m",
    isLive: true,
  },
  {
    id: "12",
    title: "Fed decision in March?",
    type: "binary",
    image: "/markets/fed.jpg",
    options: [
      { name: "50+ bps decrease", odds: 2 },
      { name: "25 bps decrease", odds: 8 },
    ],
    volume: "$30m",
  },
];

export function MarketGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {markets.map((market) => {
        if (market.category && ["NFL", "NBA", "EPL", "UFC", "COUNTER STRIKE", "LEAGUE OF LEGENDS"].includes(market.category)) {
          return <SportsMarketCard key={market.id} market={market} />;
        }
        return <MarketCard key={market.id} market={market} />;
      })}
    </div>
  );
}
