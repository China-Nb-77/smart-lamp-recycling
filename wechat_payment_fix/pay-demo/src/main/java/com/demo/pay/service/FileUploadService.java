package com.demo.pay.service;

import com.demo.pay.config.PublicAccessProperties;
import com.demo.pay.config.UploadProperties;
import com.demo.pay.dto.UploadFileResponse;
import com.demo.pay.exception.BusinessException;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Set;
import java.util.UUID;

@Service
public class FileUploadService {

    private static final long MAX_FILE_SIZE = 10L * 1024 * 1024;
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "image/jpeg",
            "image/png",
            "image/webp"
    );

    private final UploadProperties uploadProperties;
    private final PublicAccessProperties publicAccessProperties;

    public FileUploadService(UploadProperties uploadProperties,
                             PublicAccessProperties publicAccessProperties) {
        this.uploadProperties = uploadProperties;
        this.publicAccessProperties = publicAccessProperties;
    }

    public UploadFileResponse upload(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(400, "FILE_REQUIRED");
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(400, "FILE_TOO_LARGE");
        }
        if (!StringUtils.hasText(file.getContentType())
                || !ALLOWED_CONTENT_TYPES.contains(file.getContentType().toLowerCase())) {
            throw new BusinessException(400, "UNSUPPORTED_FILE_TYPE");
        }

        String originalName = StringUtils.hasText(file.getOriginalFilename())
                ? file.getOriginalFilename().trim()
                : "upload.bin";
        String extension = resolveExtension(originalName);
        String fileKey = UUID.randomUUID().toString().replace("-", "");
        String storedName = fileKey + extension;
        String dateSegment = LocalDate.now().toString();
        Path rootDir = Paths.get(uploadProperties.getStorageDir()).toAbsolutePath().normalize();
        Path targetDir = rootDir.resolve(dateSegment).normalize();
        Path targetFile = targetDir.resolve(storedName).normalize();

        if (!targetFile.startsWith(rootDir)) {
            throw new BusinessException(400, "INVALID_FILE_PATH");
        }

        try {
            Files.createDirectories(targetDir);
            Files.copy(file.getInputStream(), targetFile, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException ex) {
            throw new IllegalStateException("failed to store uploaded file", ex);
        }

        String relativePath = dateSegment + "/" + storedName;
        UploadFileResponse response = new UploadFileResponse();
        response.setSuccess(true);
        response.setFileKey(fileKey);
        response.setOriginalName(originalName);
        response.setStoredName(storedName);
        response.setContentType(file.getContentType());
        response.setFileSize(file.getSize());
        response.setRelativePath(relativePath);
        response.setPublicUrl(resolvePublicUrl(relativePath));
        response.setUploadedAt(LocalDateTime.now().toString());
        return response;
    }

    public Resource loadAsResource(String relativePath) {
        Path rootDir = Paths.get(uploadProperties.getStorageDir()).toAbsolutePath().normalize();
        Path filePath = rootDir.resolve(relativePath).normalize();
        if (!filePath.startsWith(rootDir) || !Files.exists(filePath) || Files.isDirectory(filePath)) {
            throw new BusinessException(404, "FILE_NOT_FOUND");
        }
        return new FileSystemResource(filePath);
    }

    private String resolvePublicUrl(String relativePath) {
        String normalizedPublicPath = normalizePrefix(uploadProperties.getPublicPath());
        String publicPath = normalizedPublicPath + "/" + relativePath.replace("\\", "/");
        String accessDomain = publicAccessProperties.getAccessDomain();
        if (!StringUtils.hasText(accessDomain)) {
            return publicPath;
        }
        return accessDomain + publicPath;
    }

    private String normalizePrefix(String prefix) {
        if (!StringUtils.hasText(prefix)) {
            return "/uploads";
        }
        String value = prefix.trim();
        if (!value.startsWith("/")) {
            value = "/" + value;
        }
        return value.replaceAll("/+$", "");
    }

    private String resolveExtension(String originalName) {
        int index = originalName.lastIndexOf('.');
        if (index < 0 || index == originalName.length() - 1) {
            return ".bin";
        }
        String extension = originalName.substring(index).toLowerCase();
        return extension.replaceAll("[^a-z0-9.]", "");
    }
}
