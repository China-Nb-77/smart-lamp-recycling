package com.demo.pay;

import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class FileUploadIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldUploadImageAndReturnPublicUrl() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "lamp-demo.jpg",
                MediaType.IMAGE_JPEG_VALUE,
                "fake-image-content".getBytes()
        );

        mockMvc.perform(multipart("/api/v1/files/upload").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.success").value(true))
                .andExpect(jsonPath("$.data.original_name").value("lamp-demo.jpg"))
                .andExpect(jsonPath("$.data.content_type").value(MediaType.IMAGE_JPEG_VALUE))
                .andExpect(jsonPath("$.data.relative_path", Matchers.startsWith("20")))
                .andExpect(jsonPath("$.data.public_url", Matchers.containsString("/uploads/")));
    }

    @Test
    void shouldRejectUnsupportedFileType() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "note.txt",
                MediaType.TEXT_PLAIN_VALUE,
                "plain-text".getBytes()
        );

        mockMvc.perform(multipart("/api/v1/files/upload").file(file))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("UNSUPPORTED_FILE_TYPE"));
    }
}
