package com.llmmax.webui.dto;

import java.util.List;

public record TuningSessionDto(
        String modelId,
        TuningCandidateResultDto baseline,
        List<TuningCandidateResultDto> candidates,
        TuningCandidateResultDto winner,
        String outcome,
        String reason
) {
}
