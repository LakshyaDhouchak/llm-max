package com.llmmax.webui.dto;

import java.util.List;

public record ModelSpecDto(
        String id,
        String displayName,
        String family,
        double paramSizeB,
        List<String> quantizations,
        int minVramMb,
        int recommendedVramMb,
        int minRamMb,
        String notes
) {
}
