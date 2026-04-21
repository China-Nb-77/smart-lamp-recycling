import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class TestApi {
    public static void main(String[] args) {
        try {
            String apiKey = "sk-nrgqimsclnyncxhyjmemflxuswyimgummxagsjhzqsqhwshz";
            String url = "https://api.siliconflow.cn/v1/chat/completions";
            
            String requestBody = """
                {
                    "model": "deepseek-ai/DeepSeek-V3",
                    "messages": [
                        {"role": "user", "content": "我的旧台灯能卖多少钱？"}
                    ],
                    "temperature": 0.7
                }
                """;
            
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();
            
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            System.out.println("状态码: " + response.statusCode());
            System.out.println("返回内容: " + response.body());
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}