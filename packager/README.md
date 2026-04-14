# 打包说明 — 将两个服务封装为单个 exe

概览
- 本例把两个 Java 服务（pay-demo 和 fulfillment）与一个 Python 启动器打包为单个 Windows 可执行文件。
- 启动器会并行启动两个 `java -jar` 进程并把它们的日志输出到控制台。

前提
- 在 Windows 上已安装 Java（`java` 可执行在 PATH 中）。
- 已安装 Python 3.8+。建议使用 venv 并激活。
- 安装 `pyinstaller`（构建脚本会尝试安装）。

快速构建
1. 打开 PowerShell 或 cmd，切换到仓库根目录（包含 `packager` 文件夹）。
2. 运行 `packager\build_exe.bat`。

手动运行（不打包）
```
python packager/launcher.py --jar1 wechat_payment_fix/pay-demo/target/pay-demo-patch-0.0.1-SNAPSHOT.jar \
  --jar2 "fulfillment - 副本/target/fulfillment-1.0.0.jar"
```

当用 PyInstaller 打包后，生成的 exe 会把两个 jar 解包到运行目录（内部），launcher 会按相对路径寻找它们。

注意
- 如果 `硅基流动` 的 API Key 已经写入后端代码（或读取环境变量），确保在运行 exe 前把对应环境变量设置好（例如 `set SILICON_API_KEY=...`）。
- 若需要把 Python 的 image_quote_system 一并打包为服务，请告知，我可以把第三个服务也加入到 launcher。
