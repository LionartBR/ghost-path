/* KnowledgeGraph — wrapper for the interactive React Flow DAG. */

import { useTranslation } from "react-i18next";
import FlowGraph from "./graph/FlowGraph";
import type { GraphData } from "../types";

interface KnowledgeGraphProps {
  data: GraphData;
}

export default function KnowledgeGraph({ data }: KnowledgeGraphProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col w-full h-full bg-white border border-gray-200/80 rounded-xl shadow-md shadow-gray-200/40 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
        <h2 className="text-sm font-semibold text-gray-900">{t("graph.title")}</h2>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-medium">
          {t("graph.nodeCount", { count: data.nodes.length })}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <FlowGraph data={data} />
      </div>
    </div>
  );
}
