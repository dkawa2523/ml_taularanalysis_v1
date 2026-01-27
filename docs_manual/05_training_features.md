# 本コードの学習機能

## 1. 前処理
- 数値/カテゴリ列を推定し、欠損補完→スケーリング/エンコードを適用。
- split を preprocess で固定し、train は再分割しない（比較可能性のため）。

| 前処理名 | 概要 | メリット | 想定利用ケース | ライブラリ | 入力変数への影響 | 目的変数への影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `stdscaler_ohe` | 数値: 標準化、カテゴリ: OneHot | 直線モデルに強い | 一般的な回帰/分類 | scikit-learn | 欠損補完+スケール/エンコード | 変換なし |
| `categorical.frequency` | 出現頻度エンコード | 高カーディナリティに強い | ID系/カテゴリが多い | scikit-learn | 次元爆発を抑制 | 変換なし |
| `categorical.hashing` | ハッシュエンコード | 大規模カテゴリ | 超高カーディナリティ | scikit-learn | 次元固定 | 変換なし |
| `categorical.target_mean_oof` | 目的変数の平均をOOFで付与 | 精度向上 | 目的変数と相関が強いカテゴリ | scikit-learn | 目的変数リーク抑制 | 目的変数を参照 |
| `categorical.ordinal` | 順序エンコード | 低次元で簡易 | tree系モデル | scikit-learn | 低コスト | 変換なし |

## 2. 回帰学習モデル
| モデル名 | 概要 | メリット | 想定利用ケース | ライブラリ | 特記事項 |
| --- | --- | --- | --- | --- | --- |
| ridge | L2正則化線形回帰 | 安定・高速 | 基本ベースライン | scikit-learn | 分類時はRidgeClassifier |
| lasso | L1正則化線形回帰 | 特徴選択 | 高次元で簡素化 | scikit-learn | sparsityが欲しい時 |
| elasticnet | L1+L2 | バランス良い | 中規模データ | scikit-learn | alpha/l1_ratio調整 |
| linear_regression | 最小二乗 | 解釈性 | ベースライン | scikit-learn | 正則化なし |
| random_forest | バギング木 | 非線形・頑健 | 中規模データ | scikit-learn | 重めだが安定 |
| extra_trees | 乱択木 | 高速・頑健 | 特徴量が多い | scikit-learn | 高速な木モデル |
| gradient_boosting | 勾配ブースト | 精度高 | 非線形問題 | scikit-learn | 深さ/学習率調整 |
| gaussian_process | ガウス過程 | 不確実性 | 小規模データ | scikit-learn | 計算コスト高 |
| knn | 近傍法 | シンプル | 小規模/非線形 | scikit-learn | スケール影響大 |
| svc / svr | SVM | マージン最大化 | 中規模 | scikit-learn | kernel調整 |
| mlp | 多層NN | 非線形 | 中規模 | scikit-learn | 収束に注意 |
| lgbm | LightGBM | 高精度・高速 | 大規模/高次元 | lightgbm | optional依存 |
| xgboost | XGBoost | 高精度 | 大規模/高次元 | xgboost | optional依存 |
| catboost | CatBoost | カテゴリに強い | カテゴリ多い | catboost | optional依存 |
| tabpfn | TabPFN | 小規模高精度 | 少量データ | tabpfn | optional依存/weights |

## 3. 自動アンサンブル
| アンサンブル名 | 概要 | メリット | 想定利用ケース | ライブラリ | 入力要件 |
| --- | --- | --- | --- | --- | --- |
| mean_topk | 上位Kモデル平均 | 安定・簡単 | 標準運用 | numpy | K設定のみ |
| weighted | 重み探索（simplex） | 精度向上 | 余裕がある時 | numpy | n_samples設定 |
| stacking | メタモデルで統合 | 高精度 | 高度な最適化 | scikit-learn | CV/メタモデル必要 |

## 4. モデル評価 Metrics
| Metrics名 | 概要 | メリット | 想定利用ケース | ライブラリ | 注意点 |
| --- | --- | --- | --- | --- | --- |
| r2 | 決定係数 | 直感的 | 回帰の説明力 | scikit-learn | 0未満あり |
| mse | 平均二乗誤差 | 大誤差に敏感 | 回帰 | scikit-learn | 単位依存 |
| rmse | MSEの平方根 | 解釈しやすい | 回帰 | scikit-learn | 単位依存 |
| mae | 平均絶対誤差 | ロバスト | 回帰 | scikit-learn | 外れ値に強い |
| accuracy | 正解率 | わかりやすい | 分類 | scikit-learn | 不均衡に弱い |
| f1 / fbeta | 調和平均 | 不均衡対応 | 分類 | scikit-learn | 閾値に依存 |
| roc_auc / pr_auc | AUC | 閾値非依存 | 二値分類 | scikit-learn | 確率出力必須 |
| log_loss | ログ損失 | 確率評価 | 分類 | scikit-learn | 確率出力必須 |

## 5. Leaderboard（非モデル評価基準）
| 項目 | 内容 | 目的 | 使われる箇所 | 備考 |
| --- | --- | --- | --- | --- |
| comparability | split_hash / processed_dataset_id 一致 | 公平比較 | leaderboard | 不一致は除外 |
| primary_metric | eval.primary_metric | 順位付け | leaderboard | directionに注意 |
| composite_score | scoring.weights で合成 | 複数指標の評価 | leaderboard | minmax正規化 |
| max_models | 表示上限 | UI整理 | leaderboard/report | exec_policyで制御 |
| recommend.top_k | 推奨数 | 運用判断 | recommendation.json | 既定1件 |
