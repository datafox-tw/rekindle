# infra

叢集與部署設定。階段 0 從 `kind/` 開始，階段 1 才加 GKE。

```
infra/
  kind/        本機叢集設定
  terraform/   GKE 叢集與兩個節點池
  helm/        Spark Operator 的 values
  k8s/         平台自己的服務（kustomize：base、overlays/kind、overlays/gke）
```
