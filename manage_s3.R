library(aws.s3)
library(tidyverse)

bucket <- "fbedecarrats"

objects <- get_bucket_df(bucket, region = "")

objects_to_delete <- objects %>%
  filter(str_starts(Key, "diffusion/cantines/output") & 
           str_detect(Key, "test.txt", negate = TRUE)) 

# # deletion doesn't work with aws.s3: error 403
# map(objects_to_delete$Key, delete_object, region = "")


# So we use paws package
svc <- paws::s3(config = list(
  credentials = list(
    creds = list(
      access_key_id = Sys.getenv("AWS_ACCESS_KEY_ID"),
      secret_access_key = Sys.getenv("AWS_SECRET_ACCESS_KEY"),
      session_token = Sys.getenv("AWS_SESSION_TOKEN")
    ),
    profile = "f7sggu"
  ),
  endpoint = paste0("https://", Sys.getenv("AWS_S3_ENDPOINT")),
  region = Sys.getenv("AWS_DEFAULT_REGION")
))

delete_objects_paws <- function(bucket, key_list) {
  for (i in 1:length(key_list)) {
    svc$delete_object(Bucket = bucket,
                      Key = key_list[i])
  }
}

delete_objects_paws(bucket = "fbedecarrats", key_list = objects_to_delete$Key)