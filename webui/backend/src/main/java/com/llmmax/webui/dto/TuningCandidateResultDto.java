package com.llmmax.webui.dto;

import java.util.Map;

public record TuningCandidateResultDto(
        Map<String, Object> config,
        BenchmarkResultDto benchmark
) {
}
