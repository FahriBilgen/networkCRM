import { NODE_TYPES } from '../types';
import type { EdgeResponse, GoalNetworkDiagnostics, NodeResponse } from '../types';

export function buildGoalNetworkDiagnostics(nodes: NodeResponse[], supports: EdgeResponse[]): GoalNetworkDiagnostics {
  const personLookup = new Map(nodes.filter((node) => node.type === NODE_TYPES.PERSON).map((node) => [node.id, node]));
  const supportDetails = supports
    .map((edge) => {
      const person = personLookup.get(edge.sourceNodeId);
      if (!person) {
        return null;
      }
      return {
        person,
        edge,
        daysSinceInteraction: daysSince(edge.lastInteractionDate),
      };
    })
    .filter((detail): detail is NonNullable<typeof detail> => Boolean(detail));

  const total = supportDetails.length;
  const strongCount = supportDetails.filter((detail) => (detail.edge.relationshipStrength ?? 0) >= 4).length;
  const freshCount = supportDetails.filter(
    (detail) => detail.daysSinceInteraction !== null && detail.daysSinceInteraction <= 45,
  ).length;
  const readinessScore =
    total === 0 ? 0 : Number(((strongCount / total) * 0.6 + (freshCount / total) * 0.4).toFixed(2));

  let readinessLevel: GoalNetworkDiagnostics['readiness']['level'] = 'weak';
  let readinessMessage = 'Network zayif gorunuyor, baglantilari guclendir.';
  if (readinessScore >= 0.7 || strongCount >= 3) {
    readinessLevel = 'strong';
    readinessMessage = 'Bu hedef icin network hazir gorunuyor.';
  } else if (readinessScore >= 0.45) {
    readinessLevel = 'medium';
    readinessMessage = 'Ag sinirda, yeni guclu baglantilar eklemeye calisin.';
  }
  if (total === 0) {
    readinessMessage = 'Bu hedefe bagli kisi yok.';
  }

  const readinessSummary = [
    `${total} baglanti`,
    `${strongCount} baglanti 4+ guce sahip`,
    `${freshCount} baglanti son 45 gunde temas kurdu`,
  ];
  if (total > 0 && total < 3) {
    readinessSummary.push('En az 3 destekci olmadan hedef riskli.');
  }

  const sectorHighlights = buildSectorHighlights(nodes, supportDetails);
  const riskAlerts = buildRiskAlerts(supportDetails);

  return {
    readiness: {
      level: readinessLevel,
      score: readinessScore,
      message: readinessMessage,
      summary: readinessSummary,
    },
    sectorHighlights,
    riskAlerts,
  };
}

function buildSectorHighlights(
  nodes: NodeResponse[],
  details: Array<{ person: NodeResponse; edge: EdgeResponse }>,
): string[] {
  const highlights: string[] = [];
  const coveredSectors = new Map<string, number>();
  details.forEach((detail) => {
    const sector = (detail.person.sector ?? '').trim().toLowerCase();
    if (!sector) {
      return;
    }
    coveredSectors.set(sector, (coveredSectors.get(sector) ?? 0) + 1);
  });
  if (coveredSectors.size > 0) {
    const [topSector, topCount] = [...coveredSectors.entries()].sort((a, b) => b[1] - a[1])[0];
    highlights.push(`${topCount} baglanti ${topSector} sektorunde.`);
  }

  const overallSectorCounts = new Map<string, number>();
  nodes
    .filter((node) => node.type === NODE_TYPES.PERSON)
    .forEach((node) => {
      const key = (node.sector ?? '').trim().toLowerCase();
      if (!key) {
        return;
      }
      overallSectorCounts.set(key, (overallSectorCounts.get(key) ?? 0) + 1);
    });

  const uncoveredTop = [...overallSectorCounts.entries()]
    .filter(([sector]) => sector && !coveredSectors.has(sector))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([sector]) => sector);
  if (uncoveredTop.length > 0) {
    highlights.push(`Eksik sektorler: ${uncoveredTop.join(', ')}`);
  }

  if (highlights.length === 0) {
    highlights.push('Sektor dagilimini hesaplamak icin veri yok.');
  }
  return highlights;
}

function buildRiskAlerts(details: Array<{ person: NodeResponse; edge: EdgeResponse; daysSinceInteraction: number | null }>) {
  if (details.length === 0) {
    return ['Destekci yok, once kisi ekleyin.'];
  }

  const alerts: string[] = [];
  const stale = details
    .filter((detail) => detail.daysSinceInteraction !== null && detail.daysSinceInteraction > 60)
    .sort((a, b) => (b.daysSinceInteraction ?? 0) - (a.daysSinceInteraction ?? 0))
    .slice(0, 3);
  stale.forEach((detail) => {
    alerts.push(
      `${detail.person.name ?? 'Isimsiz'} ile ${Math.round(detail.daysSinceInteraction ?? 0)} gundur iletisim yok.`,
    );
  });

  const weak = details.filter((detail) => (detail.edge.relationshipStrength ?? 0) < 3).slice(0, 3);
  weak.forEach((detail) => {
    alerts.push(
      `${detail.person.name ?? 'Isimsiz'} icin iliski gucu ${detail.edge.relationshipStrength ?? 0}/5 seviyesinde.`,
    );
  });

  if (alerts.length === 0) {
    alerts.push('Kritik risk bulunmadi.');
  }
  return alerts;
}

function daysSince(value?: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return Math.floor((Date.now() - parsed) / (1000 * 60 * 60 * 24));
}
