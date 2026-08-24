package com.llmmax.webui.dto;

public record GpuInfoDto(
        int index,
        String name,
        int totalVramMb,
        int freeVramMb,
        int usedVramMb,
        String computeCapability,
        Integer utilizationPct,
        Integer temperatureC
) {
}