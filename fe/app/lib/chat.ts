/** Ánh xạ DTO backend → mô hình UI cho chat. */

import type {
  ConversationSummaryDTO,
  Convo,
  MessageDTO,
  Msg,
  Source,
  SourceDTO,
} from "@/app/types/chat";
import { dayLabel, timeFromISO } from "@/app/lib/time";

const CONVO_TINT = "var(--brand-subtle)";
const CONVO_FG = "var(--brand-strong)";

export function sourceFromDTO(dto: SourceDTO): Source {
  return {
    index: dto.index,
    document_id: dto.document_id,
    filename: dto.filename,
    weaviate_uuid: dto.weaviate_uuid,
    snippet: dto.snippet,
    score: dto.score,
  };
}

export function msgFromDTO(dto: MessageDTO): Msg {
  const isBot = dto.sender_type === "assistant";
  return {
    from: isBot ? "bot" : "user",
    text: dto.content,
    time: timeFromISO(dto.created_at),
    sources: isBot && dto.sources?.length ? dto.sources.map(sourceFromDTO) : undefined,
  };
}

export function convoFromSummary(dto: ConversationSummaryDTO): Convo {
  return {
    id: String(dto.id),
    serverId: dto.id,
    title: dto.title,
    time: dayLabel(dto.updated_at),
    tint: CONVO_TINT,
    fg: CONVO_FG,
    messages: [],
    loaded: false,
    preview: dto.last_message ?? undefined,
  };
}
