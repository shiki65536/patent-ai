resource "aws_lambda_function" "patent_rag" {
  function_name = "patent-rag"

  package_type = "Image"

  image_uri = "${data.aws_ecr_repository.patent_rag.repository_url}@${data.aws_ecr_image.patent_rag_latest.image_digest}"

  role = aws_iam_role.lambda_role.arn

  memory_size = 1024
  timeout     = 30

  architectures = ["x86_64"]

  environment {
    variables = {
        API_SECRET            = var.api_secret
        GEMINI_API_KEY        = var.google_api_key
        GOOGLE_API_KEY        = var.google_api_key
        ANTHROPIC_API_KEY     = ""
        RATE_LIMIT_PER_HOUR   = "5"
        MAX_INPUT_CHARS       = "3000"
        DISABLE_CLAUDE        = "true"
        DAILY_COST_LIMIT_USD  = "1"
        AWS_CHROMA_DB_PATH    = "./aws_chroma_db"
    }
  }
}