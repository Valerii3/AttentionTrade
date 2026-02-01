import { Link, useSearchParams } from "react-router-dom";
import { Search, HelpCircle, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface HeaderProps {
  onOpenCreateEvent?: () => void;
}

export function Header(props: HeaderProps) {
  const { onOpenCreateEvent } = props;
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value.trim()) next.set("q", value);
        else next.delete("q");
        return next;
      },
      { replace: true }
    );
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground">
              <span className="text-sm font-bold text-background">A</span>
            </div>
            <span className="text-xl font-bold text-foreground">
              AttentionTrade
            </span>
          </Link>
        </div>

        <div className="hidden flex-1 max-w-xl mx-8 md:block">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search markets"
              value={q}
              onChange={handleSearchChange}
              className="w-full pl-10 pr-12 bg-secondary border-border text-foreground placeholder:text-muted-foreground"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground border border-border px-1.5 py-0.5 rounded">
              /
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            className="hidden sm:flex items-center gap-2 text-primary hover:text-primary/80"
          >
            <HelpCircle className="h-4 w-4" />
            <span className="hidden lg:inline">How it works</span>
          </Button>
          <Link to="/profile">
            <Button variant="ghost" className="text-foreground hover:text-foreground/80">
              Profile
            </Button>
          </Link>
          <Button
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={() => onOpenCreateEvent?.()}
          >
            Create event
          </Button>
          <Button variant="ghost" size="icon" className="text-foreground">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
