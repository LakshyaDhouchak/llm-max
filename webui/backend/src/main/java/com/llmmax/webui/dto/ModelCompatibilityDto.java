package com.llmmax.webui.dto;

public record ModelCompatibilityDto(
        ModelSpecDto model,
        String tier,
        String reason
) {
}
