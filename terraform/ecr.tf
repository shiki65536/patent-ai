data "aws_ecr_repository" "patent_rag" {
  name = "patent-rag-lambda"
}

data "aws_ecr_image" "patent_rag_latest" {
  repository_name = data.aws_ecr_repository.patent_rag.name
  image_tag       = "latest"
}