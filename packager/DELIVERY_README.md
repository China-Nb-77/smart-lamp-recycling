交付包说明

包含文件：
- `combined_services.exe` （单文件可执行，位于 dist/）
- `README.md`（packager/README.md，构建说明）
- `build_exe.bat`（packager/build_exe.bat，复现打包用）

运行前准备
1. 在 Windows 上确保已安装 Java（`java` 在 PATH 中）。
2. 确认需要的环境变量已设置，例如硅基流动 API：
   - `SILICON_API_KEY`：你的 API Key

运行示例
在命令提示符中：

```bat
set SILICON_API_KEY=你的_api_key_here
dist\combined_services.exe
```

可选参数（直接传给 exe）：
- `--jar1 <path>` 指定第一个 jar 路径（覆盖内置路径）
- `--jar2 <path>` 指定第二个 jar 路径
- `--py-host <host>` 指定内置 Python 服务 host（默认 127.0.0.1）
- `--py-port <port>` 指定内置 Python 服务 port（默认 8000）
- `--skip-jars` 仅启动 Python 服务（用于调试）

健康检查
- Python 服务健康检查：GET http://<py-host>:<py-port>/health

注意
- 生成的 exe 依赖系统上可用的 Java。如果需要把 JRE 一并打包，请告知，我会提供额外方案（体积大）。

故障排查
- 若服务未响应，检查 Java 命令是否可用：`where java`。
- 查看 Windows 防火墙或端口占用问题。

交付文件位置
- 打包结果：`dist/combined_services_package.zip`（包含 exe 和说明文件）
