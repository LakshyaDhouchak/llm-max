package com.llmmax.webui.dto;

public record RunResultDto(
        String response,
        double totalDurationS,
        int tokensGenerated,
        Double tokensPerSec,
        RunRecordDto runRecord
) {
}
