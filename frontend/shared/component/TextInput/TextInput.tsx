"use client";
import { TextField } from "../../ui/TextField";
export interface TextInputProps {
  label: string;
  name: string;
  autoComplete?: string;
  type?: "text" | "password";
  required?: boolean;
  minLength?: number;
  maxLength?: number;
}
export function TextInput({ required, ...props }: TextInputProps) {
  return <TextField {...props} isRequired={required} />;
}
