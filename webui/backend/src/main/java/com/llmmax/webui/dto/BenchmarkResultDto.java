package com.llmmax.webui.dto;

import java.util.Map;

public record BenchmarkResultDto(
        Map<String, Object> config,
        Double tokensPerSec,
        Double p50LatencyS,
        Double p95LatencyS,
        boolean oomOccurred,
        String error,
        int samplesCompleted,
        int samplesAttempted
) {
    public boolean succeeded() {
        return error == null && samplesCompleted == samplesAttempted;
    }
}
