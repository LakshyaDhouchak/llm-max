package com.llmmax.webui.dto;

import jakarta.validation.constraints.NotBlank;

public record RunRequestDto(
        @NotBlank(message = "prompt must not be blank")
        String prompt
) {
}
