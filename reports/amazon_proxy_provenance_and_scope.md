# Amazon section: educational proxy model

## Scope
This workflow uses generic customer-churn proxy files. They are not Amazon Prime Video customer data. All model metrics are educational proxy-dataset results and must not be described as Amazon Prime Video performance.

## Provenance and target
Public material associates similarly named training/testing files with the Kaggle Customer Churn Dataset (https://www.kaggle.com/datasets/muhammadshahidazeem/customer-churn-dataset). Downstream project documentation describes Churn as a 0/1 churn label, but neither the local project nor available source documentation verifies how labels were generated, the underlying data origin, the outcome window, or when features were observed. These limitations remain unresolved.

## Data handling and evaluation
The training file contains one row with every field missing. The workflow records and excludes that row from the in-memory modeling frame only; the source CSV is unchanged. CustomerID is excluded from features. The supplied testing CSV is not combined with training data and is not used for evaluation because 62,995 IDs overlap and 32,778 shared IDs have conflicting labels; all shared IDs also differ in at least one feature. The aggregate conflict audit does not expose IDs and does not discard records.

Evaluation uses a reproducible stratified 80/20 holdout from nonempty training rows with random_state=42. Imputation, scaling, and encoding are within pipelines fitted on the training split only. Since feature timing is undocumented, leakage cannot be ruled out. The results describe only this educational proxy exercise.
