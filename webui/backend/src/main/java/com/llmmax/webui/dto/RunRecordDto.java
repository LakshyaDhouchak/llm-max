package com.llmmax.webui.dto;

public record RunRecordDto(
        Long id,
        String modelId,
        String runtime,
        String prompt,
        int tokensGenerated,
        double totalDurationS,
        Double tokensPerSec,
        String createdAt
) {
}
