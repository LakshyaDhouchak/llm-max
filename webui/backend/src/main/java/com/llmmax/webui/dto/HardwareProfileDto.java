package com.llmmax.webui.dto;

import java.util.List;

public record HardwareProfileDto(
        List<GpuInfoDto> gpus,
        int cpuCoresPhysical,
        int cpuCoresLogical,
        String cpuModel,
        int totalRamMb,
        int availableRamMb
) {
    public boolean hasGpu() {
        return gpus != null && !gpus.isEmpty();
    }
}
