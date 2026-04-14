import React, {PropsWithChildren} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {shellTheme} from '../config/theme';

type Props = PropsWithChildren<{
  title: string;
  subtitle?: string;
}>;

export default function SectionCard({children, title, subtitle}: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      <View style={styles.body}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: shellTheme.colors.surface,
    borderRadius: shellTheme.radius.large,
    padding: 20,
    borderWidth: 1,
    borderColor: shellTheme.colors.border,
    gap: 10,
  },
  title: {
    color: shellTheme.colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  subtitle: {
    color: shellTheme.colors.muted,
    fontSize: 13,
    lineHeight: 20,
  },
  body: {
    gap: 12,
  },
});
