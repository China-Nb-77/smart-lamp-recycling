package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class UploadFileResponse {

    private boolean success;

    @JsonProperty("file_key")
    private String fileKey;

    @JsonProperty("original_name")
    private String originalName;

    @JsonProperty("stored_name")
    private String storedName;

    @JsonProperty("content_type")
    private String contentType;

    @JsonProperty("file_size")
    private long fileSize;

    @JsonProperty("relative_path")
    private String relativePath;

    @JsonProperty("public_url")
    private String publicUrl;

    @JsonProperty("uploaded_at")
    private String uploadedAt;
}
