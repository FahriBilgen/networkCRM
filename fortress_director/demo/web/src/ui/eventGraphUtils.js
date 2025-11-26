export function mergeEventLogEntries(
    baseEntries,
    nodeDescription,
    nodeId,
    turn,
    previousNodeId
) {
    const merged = [...baseEntries];
    if (nodeDescription) {
        merged.push({
            id: `${turn}-${nodeId ?? "event"}-description`,
            text: nodeDescription,
            turn,
            timestamp: new Date().toISOString()
        });
    }
    if (
        previousNodeId &&
        nodeId &&
        previousNodeId !== nodeId
    ) {
        merged.push({
            id: `${turn}-${nodeId}-advance`,
            text: `Event Graph advanced to: ${nodeId}`,
            turn,
            timestamp: new Date().toISOString()
        });
    }
    return merged;
}
