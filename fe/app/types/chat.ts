export type Msg = { from: "bot" | "user"; text: string; time: string };

export type Convo = {
  id: string;
  title: string;
  time: string;
  tint: string;
  fg: string;
  messages: Msg[];
};
