# 图像识别报价系统

当前仓库包含一条可运行的端到端链路：

`原始图片 -> SAM3 预标注 -> 人工审核 -> 检测训练集导出 -> RT-DETR 检测 -> ROI 裁剪 -> OpenCLIP 检索 -> 规则报价 -> LightGBM residual 修正`

本仓库已具备以下特性：

- `SAM3` 支持 `official -> bridge -> placeholder` 多级回退。
- `baseline` 评估会输出总览、明细 CSV、样例报告和可选对比报告。
- 审核结果可以直接导出下一轮训练集，并记录版本快照。
- 现有自动化测试覆盖主报价链路、审核面板、`SAM3 placeholder fallback`、`baseline` 评估、`LightGBM residual` 训练与降级、训练集版本导出、`SAM3 bridge` mock 集成。

## 安装

最小安装：

```bash
pip install -e .
```

推荐安装：

```bash
pip install -e ".[ml,serve,dev]"
```

## 快速开始

生成样例数据、预标注、审核通过样例并导出检测训练集：

```bash
python -m image_quote_system.cli prepare-data
```

构建检索索引：

```bash
python -m image_quote_system.cli build-index
```

执行单图报价：

```bash
python -m image_quote_system.cli quote-image --image data/queries/SKU-ALU-PENDANT-S_query.png --topk 3
```

生成审核面板：

```bash
python -m image_quote_system.cli audit-annotations --status-filter all --sample-size 50
```

## 真实 SAM3 接入说明

### 运行策略

`configs/system.yaml` 中的默认优先级为：

1. `official`
2. `bridge`
3. `placeholder`

行为约束如下：

- 当前 Python 进程安装了 `sam3` 且配置可用时，走 `official`。
- 当前进程不可用但外部 bridge runtime 可用时，走 `bridge`。
- 真实依赖缺失、checkpoint 未配置、bridge 失败或超时时，自动回退到 `placeholder`。

### 配置项

`configs/system.yaml`

```yaml
annotation:
  sam3:
    backend_priority: [official, bridge, placeholder]
    official:
      checkpoint: ""
      checkpoint_env: SAM3_CHECKPOINT
      model_cfg: ""
      model_cfg_env: SAM3_MODEL_CFG
      device: cuda
      device_env: SAM3_DEVICE
    bridge:
      python_executable: ""
      python_executable_env: SAM3_BRIDGE_PYTHON
      working_dir: ""
      working_dir_env: SAM3_BRIDGE_WORKDIR
      checkpoint: ""
      checkpoint_env: SAM3_CHECKPOINT
      model_cfg: ""
      model_cfg_env: SAM3_MODEL_CFG
      device: cuda
      device_env: SAM3_DEVICE
      timeout_seconds: 120
```

### 推荐接入方式

方式一：当前环境直接安装 `sam3`

```bash
set SAM3_CHECKPOINT=C:\models\sam3\sam3_large.pt
set SAM3_MODEL_CFG=C:\models\sam3\sam3_large.yaml
set SAM3_DEVICE=cuda
python -m image_quote_system.cli prelabel-sam3 --config-dir configs --raw-dir data/raw --annotation-dir data/annotations --auto-approve --reviewer bridge_smoke
```

方式二：使用独立 bridge runtime

```bash
set SAM3_BRIDGE_PYTHON=C:\venvs\sam3\python.exe
set SAM3_BRIDGE_WORKDIR=C:\repos\sam3-runtime
set SAM3_CHECKPOINT=C:\models\sam3\sam3_large.pt
set SAM3_MODEL_CFG=C:\models\sam3\sam3_large.yaml
set SAM3_DEVICE=cuda
python -m image_quote_system.cli prelabel-sam3 --config-dir configs --raw-dir data/raw --annotation-dir data/annotations --auto-approve --reviewer bridge_smoke
```

### bridge worker

bridge 模式通过本仓库脚本执行：

- `scripts/sam3_bridge_worker.py`

它会接收：

- `--image`
- `--prompt`
- `--output-json`
- `--checkpoint`
- `--model-cfg`
- `--device`

如果 bridge runtime 缺少 `sam3` 包、没有返回实例、没有产出 JSON、超时或抛错，主流程都会自动降级到 `placeholder`。

## 检测训练与推理

训练：

```bash
python -m image_quote_system.cli train-detector --epochs 1 --imgsz 320 --batch 1 --name rtdetr-lamp
```

验证：

```bash
python -m image_quote_system.cli validate-detector --weights artifacts/models/detector/rtdetr-lamp/best.pt --split val --name rtdetr-lamp-val
```

导出：

```bash
python -m image_quote_system.cli export-detector --weights artifacts/models/detector/rtdetr-lamp/best.pt --format torchscript --imgsz 320
```

## 评估输出

执行 baseline 评估：

```bash
python -m image_quote_system.cli evaluate-baseline --config-dir configs --report-name baseline_report_upgrade
```

如果要和上一版结果比对：

```bash
python -m image_quote_system.cli evaluate-baseline --config-dir configs --report-name baseline_report_upgrade --compare-to artifacts/reports/baseline_report.json
```

评估会保留原有：

- `artifacts/reports/<report_name>.json`
- `artifacts/reports/<report_name>.md`

并新增版本化目录：

- `artifacts/reports/<report_name>/summary.json`
- `artifacts/reports/<report_name>/summary.md`
- `artifacts/reports/<report_name>/case_overview.csv`
- `artifacts/reports/<report_name>/detection_details.csv`
- `artifacts/reports/<report_name>/retrieval_details.csv`
- `artifacts/reports/<report_name>/quote_details.csv`
- `artifacts/reports/<report_name>/quote_rule_details.csv`
- `artifacts/reports/<report_name>/version_manifest.json`
- `artifacts/reports/<report_name>/sample_report.md`
- `artifacts/reports/<report_name>/comparison.json`
- `artifacts/reports/<report_name>/comparison.md`

这些产物适合人工比较不同版本的：

- 检测 IoU、回退情况和低质量样例
- 检索 TopK 结果和候选排序变化
- 报价误差、规则命中与 residual 修正变化

## 审核与数据迭代

导出审核清单：

```bash
python -m image_quote_system.cli audit-annotations --status-filter all --sample-size 50
```

回写审核结果：

```bash
python -m image_quote_system.cli apply-review-decisions --decision-file artifacts/annotation_review/review_decisions.json --reviewer qa_user
```

直接导出当前审核后的训练集：

```bash
python -m image_quote_system.cli export-annotations --annotation-dir data/annotations --dataset-dir data/detection_dataset --exports-dir data/annotation_exports --category-name lamp
```

从审核结果导出下一轮训练集并记录版本：

```bash
python -m image_quote_system.cli export-training-version --config-dir configs --version-tag round-20260402-a --decision-file artifacts/annotation_review/review_decisions.json --reviewer qa_user --note "round A after qa review"
```

如果审核结果已经回写，只想做一次版本快照：

```bash
python -m image_quote_system.cli export-training-version --config-dir configs --version-tag round-20260402-b --note "snapshot after manual review"
```

版本化导出会生成：

- `artifacts/dataset_versions/<version_tag>/manifest.json`
- `artifacts/dataset_versions/<version_tag>/annotation_status.csv`
- `artifacts/dataset_versions/<version_tag>/detection_dataset/`
- `artifacts/dataset_versions/<version_tag>/annotation_exports/`

`manifest.json` 会记录：

- 版本号
- 创建时间
- 数据集快照路径
- 审核状态统计
- 审核文件 hash
- 本次导出的样本统计

## 生产部署前检查清单

上线前至少检查以下项目：

- `SAM3`：确认官方 runtime 或 bridge runtime 至少有一条真实链路可用，并完成一次 smoke run。
- checkpoint：确认 `SAM3_CHECKPOINT`、`SAM3_MODEL_CFG`、RT-DETR 权重、LightGBM residual 模型都来自同一轮版本。
- fallback：确认未接入真实 `SAM3` 时系统仍能回退到 `placeholder`，且不会阻塞数据准备。
- 审核数据：检测训练只使用 `approved` 样本，禁止直接混用 `pending`。
- 索引：catalog 更新后重新执行 `build-index`，不要在线请求时临时重建。
- 评估：至少保留一份最近线上版本的 `baseline` 报告，新的模型必须跑 `--compare-to`。
- 报价规则：`configs/pricing.yaml` 的规则版本要和 residual 训练数据版本对应。
- 部署工件：确认 `artifacts/models/detector/<run>/best.pt` 或导出件、`artifacts/models/lightgbm_residual.txt`、索引元数据均存在。
- API：如果要生产化 `serve-api`，需在外层补鉴权、限流、超时和日志，不要把默认示例服务直接暴露公网。
- 回滚：保留上一版 detector、index、pricing config、residual model 和 baseline 报告，确保可回切。

## 测试

运行全部测试：

```bash
python -m pytest -q
```

当前测试覆盖：

- 主报价链路
- 审核面板生成
- `SAM3 placeholder fallback`
- `SAM3 bridge` mock 集成
- 可选真实 `SAM3 bridge` smoke test（环境变量未配置时自动 skip）
- `baseline` 评估与明细产物
- `LightGBM residual` 训练与缺依赖降级
- 训练集版本化导出

## 关键路径文件

- `image_quote_system/annotation/sam3_adapter.py`
- `scripts/sam3_bridge_worker.py`
- `image_quote_system/annotation/pipeline.py`
- `image_quote_system/baseline.py`
- `image_quote_system/cli.py`
- `tests/test_end_to_end.py`

## SAM3 Community Checkpoint

See `SAM3_COMMUNITY_SETUP.md` for the community checkpoint flow based on
`AEmotionStudio/sam3` and local `.safetensors` loading.
## Agent API

- Frontend now consumes unified agent endpoints under `/vision-api/agent/*`.
- Default backend mode is `AI_LIGHT_AGENT_MODE=mock`.
- Frontend no longer needs direct rule/retrieval/model access for the main trade-in flow.

## Call Chain

1. `POST /agent/sessions`
2. `POST /agent/sessions/{session_id}/image`
3. `POST /agent/sessions/{session_id}/messages`
4. `POST /agent/sessions/{session_id}/recommendations/select`
5. `GET /agent/forms/checkout?session_id=...`
6. `POST /agent/addresses/locate` or `POST /agent/addresses/normalize`
7. `POST /agent/orders`
8. `POST /agent/orders/{order_id}/qr`
9. `GET /agent/orders/{order_id}`
10. `GET /agent/orders/{order_id}/electronic?qrToken=...`
11. `GET /agent/orders/{order_id}/logistics`
12. `GET /agent/orders/{order_id}/logistics-map`

## Session State

- Backend session keeps `quote_payload`, `preferences`, `recommendation_payload`, `selected_recommendation`, `order_id`.
- Frontend only stores UI message history and active `sessionId`.

## Auth

- Local demo currently runs without auth.
- Production TODO: add bearer token or signed session token at the gateway.

## Error Codes

- `400`: invalid or missing request fields
- `404`: session/order/qr token not found
- `500`: backend tool or adapter failure

## Mock And Real

- Mock mode: `AI_LIGHT_AGENT_MODE=mock`
- Real mode entry point reserved: `AI_LIGHT_AGENT_MODE=real`
- TODO for real mode:
  - real LLM tool-calling orchestrator
  - real payment/order adapter
  - real geocode adapter
  - real logistics adapter

## Tests

- `python -m unittest tests.test_agent_api`
- Covers image upload recognition API, quote API, recommend API, form submit API, QR order API, order status API, logistics API, logistics map API, agent session API.
