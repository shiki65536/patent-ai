resource "aws_budgets_budget" "monthly" {
  name         = "patent-rag-budget"
  budget_type  = "COST"
  limit_amount = "10"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}