import { useState } from "react";
import {
  FinancialCard,
  FinancialCardContent,
  FinancialCardHeader,
  FinancialCardTitle,
  FinancialCardDescription,
} from "@/components/ui/financial-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronLeft,
  ChevronRight,
  Lightbulb,
  Calendar,
  DollarSign,
  BarChart3,
  Bell,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ----------------------------------------------------------
// Types
// ----------------------------------------------------------
interface CategoryTotal {
  name: string;
  amount: number;
}

interface BiggestExpense {
  notes: string;
  amount: number;
  date: string;
  category: string;
}

interface BillDue {
  name: string;
  amount: number;
  due: string;
}

interface DigestData {
  week_label: string;
  start_date: string;
  end_date: string;
  total_spent: number;
  total_income: number;
  top_categories: CategoryTotal[];
  daily_breakdown: Record<string, number>;
  week_over_week_change: number | null;
  biggest_expense: BiggestExpense | null;
  insight: string;
  bills_due_next_week: BillDue[];
}

// ----------------------------------------------------------
// Mock data (replace with API call when backend is wired)
// ----------------------------------------------------------
const MOCK_DIGEST: DigestData = {
  week_label: "Week of Mar 24, 2026",
  start_date: "2026-03-24",
  end_date: "2026-03-30",
  total_spent: 1243.50,
  total_income: 2800.00,
  top_categories: [
    { name: "Food & Dining", amount: 412.30 },
    { name: "Transportation", amount: 215.00 },
    { name: "Entertainment", amount: 189.20 },
    { name: "Groceries", amount: 145.00 },
    { name: "Utilities", amount: 92.00 },
  ],
  daily_breakdown: {
    "2026-03-24": 85.20,
    "2026-03-25": 210.00,
    "2026-03-26": 195.30,
    "2026-03-27": 320.50,
    "2026-03-28": 102.00,
    "2026-03-29": 195.50,
    "2026-03-30": 135.00,
  },
  week_over_week_change: -12.4,
  biggest_expense: {
    notes: "Dinner at Nobu",
    amount: 210.00,
    date: "2026-03-25",
    category: "Food & Dining",
  },
  insight:
    "Spending down 12.4% vs last week. Biggest category: Food & Dining ($412.30).",
  bills_due_next_week: [
    { name: "Netflix", amount: 15.99, due: "2026-04-01" },
    { name: "Internet", amount: 59.99, due: "2026-04-02" },
  ],
};

// ----------------------------------------------------------
// Helpers
// ----------------------------------------------------------
function WoWBadge({ change }: { change: number | null }) {
  if (change === null) return <Badge variant="secondary">No prior data</Badge>;
  if (Math.abs(change) < 0.5)
    return (
      <Badge variant="secondary" className="flex items-center gap-1">
        <Minus className="h-3 w-3" />
        Flat
      </Badge>
    );
  if (change > 0)
    return (
      <Badge variant="destructive" className="flex items-center gap-1">
        <TrendingUp className="h-3 w-3" />+{change.toFixed(1)}%
      </Badge>
    );
  return (
    <Badge className="flex items-center gap-1 bg-success text-success-foreground">
      <TrendingDown className="h-3 w-3" />
      {change.toFixed(1)}%
    </Badge>
  );
}

const MAX_BAR = 350;

// ----------------------------------------------------------
// Component
// ----------------------------------------------------------
export function WeeklyDigest() {
  const [offset, setOffset] = useState(-1); // -1 = last complete week
  // In production replace MOCK_DIGEST with a React-Query useQuery call to /api/digest
  const digest: DigestData = MOCK_DIGEST;

  const maxDaily = Math.max(...Object.values(digest.daily_breakdown), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Weekly Digest</h1>
          <p className="text-muted-foreground">
            Spending trends & insights — {digest.week_label}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setOffset((o) => o - 1)}
            aria-label="Previous week"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">
            {offset === -1 ? "Last week" : offset === 0 ? "This week" : `${Math.abs(offset)}w ago`}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setOffset((o) => Math.min(o + 1, 0))}
            disabled={offset >= 0}
            aria-label="Next week"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Summary row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-destructive" />
              Total Spent
            </FinancialCardTitle>
          </FinancialCardHeader>
          <FinancialCardContent>
            <p className="text-2xl font-bold">${digest.total_spent.toLocaleString()}</p>
            <div className="mt-1">
              <WoWBadge change={digest.week_over_week_change} />
            </div>
          </FinancialCardContent>
        </FinancialCard>

        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              Total Income
            </FinancialCardTitle>
          </FinancialCardHeader>
          <FinancialCardContent>
            <p className="text-2xl font-bold text-success">
              ${digest.total_income.toLocaleString()}
            </p>
          </FinancialCardContent>
        </FinancialCard>

        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-primary" />
              Period
            </FinancialCardTitle>
          </FinancialCardHeader>
          <FinancialCardContent>
            <p className="text-sm font-medium">
              {new Date(digest.start_date).toLocaleDateString()} –{" "}
              {new Date(digest.end_date).toLocaleDateString()}
            </p>
          </FinancialCardContent>
        </FinancialCard>

        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle className="flex items-center gap-2 text-sm">
              <Lightbulb className="h-4 w-4 text-warning" />
              Insight
            </FinancialCardTitle>
          </FinancialCardHeader>
          <FinancialCardContent>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {digest.insight}
            </p>
          </FinancialCardContent>
        </FinancialCard>
      </div>

      {/* Main content */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Daily breakdown chart */}
        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Daily Spending
            </FinancialCardTitle>
          </FinancialCardHeader>
          <FinancialCardContent>
            <div className="space-y-2">
              {Object.entries(digest.daily_breakdown).map(([date, amount]) => {
                const barPct = (amount / maxDaily) * 100;
                const dayLabel = new Date(date).toLocaleDateString("en-US", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                });
                return (
                  <div key={date} className="flex items-center gap-3">
                    <span className="w-24 shrink-0 text-xs text-muted-foreground">
                      {dayLabel}
                    </span>
                    <div className="flex-1 rounded-full bg-muted overflow-hidden h-4">
                      <div
                        className="h-4 rounded-full bg-primary transition-all"
                        style={{ width: `${barPct}%` }}
                        aria-label={`${dayLabel}: $${amount}`}
                      />
                    </div>
                    <span className="w-16 text-right text-xs font-medium">
                      ${amount.toLocaleString()}
                    </span>
                  </div>
                );
              })}
            </div>
          </FinancialCardContent>
        </FinancialCard>

        {/* Top categories */}
        <FinancialCard>
          <FinancialCardHeader>
            <FinancialCardTitle>Top Categories</FinancialCardTitle>
            <FinancialCardDescription>Highest spend this week</FinancialCardDescription>
          </FinancialCardHeader>
          <FinancialCardContent>
            <ol className="space-y-3">
              {digest.top_categories.map((cat, i) => (
                <li key={cat.name} className="flex items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-sm">{cat.name}</span>
                  <span className="text-sm font-semibold">
                    ${cat.amount.toLocaleString()}
                  </span>
                </li>
              ))}
            </ol>
          </FinancialCardContent>
        </FinancialCard>
      </div>

      {/* Biggest expense + bills */}
      <div className="grid gap-4 lg:grid-cols-2">
        {digest.biggest_expense && (
          <FinancialCard>
            <FinancialCardHeader>
              <FinancialCardTitle className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-destructive" />
                Biggest Single Expense
              </FinancialCardTitle>
            </FinancialCardHeader>
            <FinancialCardContent className="space-y-2">
              <p className="text-lg font-bold">
                ${digest.biggest_expense.amount.toLocaleString()}
              </p>
              <p className="text-sm text-muted-foreground">
                {digest.biggest_expense.notes}
              </p>
              <div className="flex gap-2">
                <Badge variant="secondary">{digest.biggest_expense.category}</Badge>
                <Badge variant="outline">
                  {new Date(digest.biggest_expense.date).toLocaleDateString()}
                </Badge>
              </div>
            </FinancialCardContent>
          </FinancialCard>
        )}

        {digest.bills_due_next_week.length > 0 && (
          <FinancialCard>
            <FinancialCardHeader>
              <FinancialCardTitle className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-warning" />
                Bills Due Next Week
              </FinancialCardTitle>
            </FinancialCardHeader>
            <FinancialCardContent>
              <ul className="space-y-2">
                {digest.bills_due_next_week.map((bill) => (
                  <li key={bill.name} className="flex items-center justify-between text-sm">
                    <span>{bill.name}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {new Date(bill.due).toLocaleDateString()}
                      </Badge>
                      <span className="font-medium">${bill.amount.toLocaleString()}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </FinancialCardContent>
          </FinancialCard>
        )}
      </div>
    </div>
  );
}
