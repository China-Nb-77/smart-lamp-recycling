package com.demo.pay.controller;

import com.demo.pay.dto.UploadFileResponse;
import com.demo.pay.service.FileUploadService;
import com.demo.pay.util.ApiResponse;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping
public class FileUploadController {

    private final FileUploadService fileUploadService;

    public FileUploadController(FileUploadService fileUploadService) {
        this.fileUploadService = fileUploadService;
    }

    @PostMapping({"/api/v1/files/upload", "/files/upload"})
    public ApiResponse<UploadFileResponse> upload(@RequestParam("file") MultipartFile file) {
        return ApiResponse.success(fileUploadService.upload(file));
    }

    @GetMapping("/uploads/{date}/{storedName}")
    public ResponseEntity<Resource> read(@PathVariable String date,
                                         @PathVariable String storedName) {
        String relativePath = date + "/" + storedName;
        Resource resource = fileUploadService.loadAsResource(relativePath);
        return ResponseEntity.ok()
                .header(HttpHeaders.CACHE_CONTROL, "public, max-age=31536000")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(resource);
    }
}
