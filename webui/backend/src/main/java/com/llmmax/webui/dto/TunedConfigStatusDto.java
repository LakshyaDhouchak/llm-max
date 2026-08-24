package com.llmmax.webui.dto;

import java.util.Map;

public record TunedConfigStatusDto(
        String modelId,
        Map<String, Object> config,
        boolean isLocked,
        String createdAt,
        boolean hasConfig
) {
}
