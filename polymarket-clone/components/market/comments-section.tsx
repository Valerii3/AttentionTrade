"use client";

import { useState } from "react";
import { Heart, MoreHorizontal, ChevronDown, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

const tabs = [
  { id: "comments", label: "Comments", count: 168 },
  { id: "holders", label: "Top Holders" },
  { id: "activity", label: "Activity" },
];

interface Comment {
  id: string;
  username: string;
  avatar: string;
  avatarBg: string;
  time: string;
  content: string;
  likes: number;
  isLiked: boolean;
  replies: number;
  badge?: {
    text: string;
    color: string;
  };
}

const sampleComments: Comment[] = [
  {
    id: "1",
    username: "Exhausted-Start",
    avatar: "ES",
    avatarBg: "bg-orange-500",
    time: "9h ago",
    content: "Can someone give this poor black man 1 dollar?",
    likes: 1,
    isLiked: false,
    replies: 1,
  },
  {
    id: "2",
    username: "CryptoTrader99",
    avatar: "CT",
    avatarBg: "bg-blue-500",
    time: "7h ago",
    content: "This market is wild! The volatility is insane today.",
    likes: 5,
    isLiked: true,
    replies: 3,
    badge: {
      text: "Top Holder",
      color: "bg-primary",
    },
  },
  {
    id: "3",
    username: "MarketWatcher",
    avatar: "MW",
    avatarBg: "bg-green-500",
    time: "5h ago",
    content: "Based on recent news, I think the market will recover. Stay patient.",
    likes: 12,
    isLiked: false,
    replies: 0,
  },
];

function CommentItem({ comment }: { comment: Comment }) {
  const [liked, setLiked] = useState(comment.isLiked);
  const [likes, setLikes] = useState(comment.likes);
  const [showReplies, setShowReplies] = useState(false);

  const handleLike = () => {
    setLiked(!liked);
    setLikes(liked ? likes - 1 : likes + 1);
  };

  return (
    <div className="py-4">
      <div className="flex gap-3">
        <div
          className={`w-10 h-10 rounded-full ${comment.avatarBg} flex items-center justify-center text-white font-medium text-sm shrink-0`}
        >
          {comment.avatar}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-foreground font-medium text-sm">
              {comment.username}
            </span>
            {comment.badge && (
              <span
                className={`${comment.badge.color} text-xs px-2 py-0.5 rounded text-foreground`}
              >
                {comment.badge.text}
              </span>
            )}
            <span className="text-muted-foreground text-xs">{comment.time}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 ml-auto text-muted-foreground"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-foreground text-sm mb-2">{comment.content}</p>
          <div className="flex items-center gap-4">
            <button
              onClick={handleLike}
              className={`flex items-center gap-1 text-sm ${
                liked ? "text-destructive" : "text-muted-foreground"
              } hover:text-destructive transition-colors`}
            >
              <Heart className={`h-4 w-4 ${liked ? "fill-current" : ""}`} />
              {likes > 0 && <span>{likes}</span>}
            </button>
            {comment.replies > 0 && (
              <button
                onClick={() => setShowReplies(!showReplies)}
                className="text-primary text-sm hover:underline"
              >
                {showReplies ? "Hide" : "Show"} {comment.replies}{" "}
                {comment.replies === 1 ? "Reply" : "Replies"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function CommentsSection() {
  const [activeTab, setActiveTab] = useState("comments");
  const [comment, setComment] = useState("");
  const [holdersOnly, setHoldersOnly] = useState(false);

  return (
    <div className="mt-8">
      {/* Tabs */}
      <div className="flex gap-6 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.id
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
            {tab.count && ` (${tab.count})`}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Comment input */}
      <div className="flex gap-2 mt-4">
        <Input
          placeholder="Add a comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="flex-1 bg-card border-border text-foreground placeholder:text-muted-foreground"
        />
        <Button
          variant="ghost"
          className="text-primary hover:text-primary/80 font-medium"
        >
          Post
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="bg-secondary border-border text-foreground rounded-full px-4 h-9"
          >
            Newest <ChevronDown className="h-4 w-4 ml-1" />
          </Button>
          <div className="flex items-center gap-2">
            <Checkbox
              id="holders"
              checked={holdersOnly}
              onCheckedChange={(checked) => setHoldersOnly(checked as boolean)}
              className="border-muted-foreground data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            />
            <label
              htmlFor="holders"
              className="text-foreground text-sm cursor-pointer"
            >
              Holders
            </label>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-secondary/50 rounded-full px-3 py-1.5">
          <AlertCircle className="h-4 w-4 text-primary" />
          <span className="text-foreground text-sm">Beware of external links.</span>
        </div>
      </div>

      {/* Comments list */}
      <div className="divide-y divide-border">
        {sampleComments.map((c) => (
          <CommentItem key={c.id} comment={c} />
        ))}
      </div>
    </div>
  );
}
